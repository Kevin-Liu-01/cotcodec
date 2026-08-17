//! CoTCodec exact-source, multi-restart Memoria lifecycle falsifier.

use memoria_core::{Memory, MemoryType, TrustTier};
use memoria_git::GitForDataService;
use memoria_storage::SqlMemoryStore;
use serde_json::json;
use sqlx::{mysql::MySqlPool, Row};
use std::time::Duration;

const DB_NAME: &str = "cotcodec_memoria_lifecycle";
const MAIN_ID: &str = "cotcodec-main-a";
const OTHER_ID: &str = "cotcodec-main-b";
const BRANCH_ID: &str = "cotcodec-branch-a";
const POST_ID: &str = "cotcodec-post-snapshot";
const USER_A: &str = "cotcodec-user-a";
const USER_B: &str = "cotcodec-user-b";
const SNAPSHOT: &str = "cotcodec_snap_v1";
const BRANCH: &str = "cotcodec_branch_v1";

fn make_memory(id: &str, user: &str, content: &str) -> Memory {
    Memory {
        memory_id: id.to_string(),
        user_id: user.to_string(),
        memory_type: MemoryType::Semantic,
        content: content.to_string(),
        embedding: None,
        session_id: Some("cotcodec-session".to_string()),
        source_event_ids: vec![format!("source:{id}")],
        extra_metadata: None,
        is_active: true,
        superseded_by: None,
        trust_tier: TrustTier::T2Curated,
        initial_confidence: 1.0,
        access_count: 0,
        retrieval_score: None,
        observed_at: None,
        created_at: None,
        updated_at: None,
        author_id: Some("cotcodec".to_string()),
        subject_id: None,
    }
}

async fn connect_base() -> MySqlPool {
    let base = std::env::var("COTCODEC_DATABASE_BASE_URL")
        .unwrap_or_else(|_| "mysql://root:111@matrixone:6001".to_string());
    let mut last = None;
    for _ in 0..90 {
        match MySqlPool::connect(&base).await {
            Ok(pool) => return pool,
            Err(error) => {
                last = Some(error);
                tokio::time::sleep(Duration::from_secs(1)).await;
            }
        }
    }
    panic!("MatrixOne did not become ready: {:?}", last);
}

async fn connect_db() -> (SqlMemoryStore, GitForDataService) {
    let url = format!(
        "{}/{}",
        std::env::var("COTCODEC_DATABASE_BASE_URL")
            .unwrap_or_else(|_| "mysql://root:111@matrixone:6001".to_string()),
        DB_NAME
    );
    let pool = MySqlPool::connect(&url).await.expect("connect lifecycle database");
    let store = SqlMemoryStore::new(pool.clone(), 4, "cotcodec-doctor".to_string());
    store.migrate().await.expect("migrate lifecycle schema");
    let git = GitForDataService::new(pool, DB_NAME);
    (store, git)
}

async fn scalar_i64(pool: &MySqlPool, sql: &str) -> i64 {
    sqlx::query(sql)
        .fetch_one(pool)
        .await
        .expect("scalar query")
        .try_get::<i64, _>(0)
        .expect("integer scalar")
}

async fn phase_one() -> serde_json::Value {
    let base = connect_base().await;
    sqlx::raw_sql(&format!("DROP DATABASE IF EXISTS `{DB_NAME}`"))
        .execute(&base)
        .await
        .expect("drop stale lifecycle database");
    sqlx::raw_sql(&format!("CREATE DATABASE `{DB_NAME}`"))
        .execute(&base)
        .await
        .expect("create lifecycle database");
    drop(base);

    let (store, git) = connect_db().await;
    store
        .insert_into("mem_memories", &make_memory(MAIN_ID, USER_A, "main-a-v1"))
        .await
        .expect("insert user a");
    store
        .insert_into("mem_memories", &make_memory(OTHER_ID, USER_B, "main-b-v1"))
        .await
        .expect("insert user b");
    git.create_snapshot(SNAPSHOT).await.expect("create snapshot");
    git.create_branch(BRANCH, "mem_memories")
        .await
        .expect("create native branch");

    let branch_other = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM `{BRANCH}` WHERE user_id = '{USER_B}'"),
    )
    .await;
    sqlx::query(&format!(
        "UPDATE `{BRANCH}` SET content = 'branch-a-v2' WHERE memory_id = ?"
    ))
    .bind(MAIN_ID)
    .execute(store.pool())
    .await
    .expect("update branch copy");
    sqlx::query("UPDATE mem_memories SET content = 'main-a-concurrent' WHERE memory_id = ?")
        .bind(MAIN_ID)
        .execute(store.pool())
        .await
        .expect("update main concurrently");
    store
        .insert_into(BRANCH, &make_memory(BRANCH_ID, USER_A, "branch-only-a"))
        .await
        .expect("insert branch-only row");
    let main = store
        .get_from("mem_memories", MAIN_ID)
        .await
        .expect("read main")
        .expect("main exists");
    let branch = store
        .get_from(BRANCH, MAIN_ID)
        .await
        .expect("read branch")
        .expect("branch exists");
    json!({
        "phase": 1,
        "snapshot_created": git.get_snapshot(SNAPSHOT).await.unwrap().is_some(),
        "branch_isolated_from_main": main.content == "main-a-concurrent" && branch.content == "branch-a-v2",
        "shared_database_branch_contains_other_user_rows": branch_other == 1,
    })
}

async fn phase_two() -> serde_json::Value {
    let (store, git) = connect_db().await;
    let persisted = git.get_snapshot(SNAPSHOT).await.unwrap().is_some()
        && store.get_from(BRANCH, BRANCH_ID).await.unwrap().is_some();
    git.merge_branch(BRANCH, "mem_memories")
        .await
        .expect("merge branch first time");
    let first_count = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{BRANCH_ID}'"),
    )
    .await;
    git.merge_branch(BRANCH, "mem_memories")
        .await
        .expect("merge branch second time");
    let second_count = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{BRANCH_ID}'"),
    )
    .await;
    let main = store.get_from("mem_memories", MAIN_ID).await.unwrap().unwrap();
    store
        .insert_into("mem_memories", &make_memory(POST_ID, USER_A, "post-snapshot"))
        .await
        .expect("insert post-snapshot row");
    git.restore_table_from_snapshot("mem_memories", SNAPSHOT)
        .await
        .expect("restore table from snapshot");
    let restored_total = scalar_i64(store.pool(), "SELECT COUNT(*) FROM mem_memories").await;
    let restored_post = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{POST_ID}'"),
    )
    .await;
    let first_purge = store.soft_delete_from("mem_memories", MAIN_ID).await.unwrap();
    let second_purge = store.soft_delete_from("mem_memories", MAIN_ID).await.unwrap();
    let physical_residue = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{MAIN_ID}'"),
    )
    .await;
    let active_residue = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{MAIN_ID}' AND is_active = 1"),
    )
    .await;
    git.drop_branch(BRANCH).await.expect("drop branch");
    git.drop_snapshot(SNAPSHOT).await.expect("drop snapshot");
    json!({
        "phase": 2,
        "state_survived_first_restart": persisted,
        "native_merge_added_branch_row": first_count == 1,
        "native_merge_idempotent": first_count == 1 && second_count == 1,
        "conflicting_main_value_kept": main.content == "main-a-concurrent",
        "snapshot_restore_positive_path": restored_total == 2 && restored_post == 0,
        "soft_purge_is_idempotent_underneath": first_purge == 1 && second_purge == 0,
        "purge_leaves_inactive_memory_row": physical_residue == 1 && active_residue == 0,
    })
}

async fn phase_three() -> serde_json::Value {
    let (store, git) = connect_db().await;
    let physical_residue = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{MAIN_ID}'"),
    )
    .await;
    let active_residue = scalar_i64(
        store.pool(),
        &format!("SELECT COUNT(*) FROM mem_memories WHERE memory_id = '{MAIN_ID}' AND is_active = 1"),
    )
    .await;
    let branch_absent = sqlx::query(&format!("SELECT COUNT(*) FROM `{BRANCH}`"))
        .fetch_one(store.pool())
        .await
        .is_err();
    let snapshot_absent = git.get_snapshot(SNAPSHOT).await.unwrap().is_none();
    json!({
        "phase": 3,
        "state_survived_second_restart": physical_residue == 1 && active_residue == 0,
        "purge_residue_survived_restart": physical_residue == 1,
        "branch_drop_survived_restart": branch_absent,
        "snapshot_drop_survived_restart": snapshot_absent,
    })
}

#[tokio::test]
async fn cotcodec_memoria_lifecycle() {
    let phase = std::env::var("COTCODEC_PHASE").unwrap_or_else(|_| "1".to_string());
    let report = match phase.as_str() {
        "1" => phase_one().await,
        "2" => phase_two().await,
        "3" => phase_three().await,
        other => panic!("unsupported COTCODEC_PHASE={other}"),
    };
    println!("COTCODEC_MEMORIA_PHASE={report}");
}
