use chrono::{Duration, Utc};
use serde_json::json;
use shodh_memory::memory::{
    Experience, ForgetCriteria, Memory, MemoryConfig, MemoryId, MemorySystem, MemoryTier,
};
use std::fs;
use std::path::{Path, PathBuf};
use uuid::Uuid;

fn config(path: &Path) -> MemoryConfig {
    MemoryConfig {
        storage_path: path.to_path_buf(),
        working_memory_size: 4,
        session_memory_size_mb: 8,
        max_heap_per_user_mb: 128,
        auto_compress: false,
        compression_age_days: 30,
        importance_threshold: 0.90,
    }
}

fn experience(content: &str, importance: f32) -> Experience {
    Experience {
        content: content.to_owned(),
        importance_override: Some(importance),
        embeddings: Some(vec![0.01; 384]),
        ..Experience::default()
    }
}

fn contains_bytes(path: &Path, needle: &[u8]) -> bool {
    let Ok(metadata) = fs::symlink_metadata(path) else {
        return false;
    };
    if metadata.file_type().is_symlink() {
        return false;
    }
    if metadata.is_file() {
        return fs::read(path)
            .map(|bytes| bytes.windows(needle.len()).any(|window| window == needle))
            .unwrap_or(false);
    }
    if !metadata.is_dir() {
        return false;
    }
    fs::read_dir(path)
        .map(|entries| {
            entries
                .filter_map(Result::ok)
                .any(|entry| contains_bytes(&entry.path(), needle))
        })
        .unwrap_or(false)
}

fn main() -> anyhow::Result<()> {
    let root = PathBuf::from(format!("/tmp/cotcodec-shodh-doctor-{}", Uuid::new_v4()));
    fs::create_dir(&root)?;

    // A newly written Working record is already present in RocksDB. The tier
    // counts therefore overlap; they are not disjoint residency counts.
    let dual_path = root.join("dual-residency");
    let dual_config = config(&dual_path);
    let dual_id;
    let before_restart;
    {
        let system = MemorySystem::new(dual_config.clone(), None)?;
        dual_id = system.remember(
            experience("COTCODEC_SHODH_DUAL_RESIDENCY_CANARY", 0.20),
            None,
        )?;
        system.flush_storage()?;
        let stats = system.stats();
        let stored = system.get_memory(&dual_id)?;
        before_restart = json!({
            "total": stats.total_memories,
            "working": stats.working_memory_count,
            "session": stats.session_memory_count,
            "long_term": stats.long_term_memory_count,
            "stored_tier": format!("{:?}", stored.tier),
            "storage_total": system.get_storage_stats()?.total_count,
        });
    }
    let after_restart;
    {
        let system = MemorySystem::new(dual_config.clone(), None)?;
        let stats = system.stats();
        let stored = system.get_memory(&dual_id)?;
        after_restart = json!({
            "total": stats.total_memories,
            "working": stats.working_memory_count,
            "session": stats.session_memory_count,
            "long_term": stats.long_term_memory_count,
            "stored_tier": format!("{:?}", stored.tier),
            "storage_total": system.get_storage_stats()?.total_count,
        });
    }

    // Construct a state reachable when a normally promoted Session record is
    // shut down and later crosses the 24-hour threshold while offline. On
    // restart the in-memory Session map is empty, so maintenance cannot advance
    // the durable Session record to LongTerm.
    let stranded_path = root.join("stranded-session");
    let stranded_config = config(&stranded_path);
    let stranded_id = MemoryId(Uuid::new_v4());
    {
        let system = MemorySystem::new(stranded_config.clone(), None)?;
        let mut memory = Memory::new(
            stranded_id.clone(),
            experience("COTCODEC_SHODH_STRANDED_SESSION_CANARY", 0.90),
            0.90,
            None,
            None,
            None,
            Some(Utc::now() - Duration::hours(26)),
        );
        memory.promote();
        assert_eq!(memory.tier, MemoryTier::Session);
        system.storage().store(&memory)?;
        system.flush_storage()?;
    }
    let stranded_before;
    let stranded_after;
    {
        let system = MemorySystem::new(stranded_config.clone(), None)?;
        let stats = system.stats();
        stranded_before = json!({
            "working": stats.working_memory_count,
            "session": stats.session_memory_count,
            "long_term": stats.long_term_memory_count,
            "stored_tier": format!("{:?}", system.get_memory(&stranded_id)?.tier),
        });
        system.run_maintenance(1.0, "cotcodec-doctor", false)?;
        stranded_after = json!({
            "stored_tier": format!("{:?}", system.get_memory(&stranded_id)?.tier),
            "promotions_to_longterm": system.stats().promotions_to_longterm,
        });
    }

    // The public GDPR `All` path deletes logical records but counts one unique
    // record once per overlapping tier. The raw-byte probe is deliberately
    // reported in both directions; absence of a byte substring is not a proof
    // of physical erasure from compressed storage media.
    let purge_path = root.join("purge");
    let purge_config = config(&purge_path);
    let purge_canary = "COTCODEC_SHODH_PURGE_CANARY_9f76f75f2a34b55d_REPEAT_".repeat(32);
    let purge_id;
    let forget_returned;
    let logical_get_failed;
    let plaintext_present_before_forget;
    {
        let system = MemorySystem::new(purge_config.clone(), None)?;
        purge_id = system.remember(experience(&purge_canary, 0.20), None)?;
        system.flush_storage()?;
        plaintext_present_before_forget = contains_bytes(&purge_path, purge_canary.as_bytes());
        forget_returned = system.forget(ForgetCriteria::All)?;
        system.flush_storage()?;
        logical_get_failed = system.get_memory(&purge_id).is_err();
    }
    let reopened = MemorySystem::new(purge_config, None)?;
    let after_forget_stats = reopened.stats();
    drop(reopened);
    let plaintext_residue = contains_bytes(&purge_path, purge_canary.as_bytes());

    let report = json!({
        "schema_version": 1,
        "system_id": "shodh-memory-98c6e48-tier-admission-v1",
        "status": "BLOCKED_OVERLAPPING_RESIDENCY_AND_RESTART_STRANDING",
        "scientific_result": false,
        "publication_ready": false,
        "h100_actor_admission": false,
        "checks": {
            "new_working_record_already_in_long_term_storage": before_restart["working"] == 1
                && before_restart["long_term"] == 1
                && before_restart["storage_total"] == 1,
            "restart_drops_active_caches": after_restart["working"] == 0
                && after_restart["session"] == 0
                && after_restart["long_term"] == 1,
            "restart_preserves_stale_working_tier_label": after_restart["stored_tier"] == "Working",
            "eligible_persisted_session_is_stranded_after_restart":
                stranded_before["session"] == 0
                && stranded_before["stored_tier"] == "Session"
                && stranded_after["stored_tier"] == "Session"
                && stranded_after["promotions_to_longterm"] == 0,
            "logical_forget_all_hides_record_after_restart": logical_get_failed
                && after_forget_stats.total_memories == 0,
            "forget_all_return_overcounts_overlapping_tiers": forget_returned > 1,
            "plaintext_residue_not_observed_after_forget_all": !plaintext_residue,
        },
        "observations": {
            "before_restart": before_restart,
            "after_restart": after_restart,
            "stranded_before_maintenance": stranded_before,
            "stranded_after_maintenance": stranded_after,
            "forget_all_returned": forget_returned,
            "post_forget_total": after_forget_stats.total_memories,
            "plaintext_present_before_forget": plaintext_present_before_forget,
            "plaintext_residue": plaintext_residue,
        },
    });

    println!("COTCODEC_SHODH_REPORT={}", serde_json::to_string(&report)?);
    Ok(())
}
