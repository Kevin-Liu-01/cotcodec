using System.Diagnostics;
using System.Text.Json;
using TotalRecall.Core;
using TotalRecall.Infrastructure.Embedding;
using TotalRecall.Infrastructure.Memory;
using TotalRecall.Infrastructure.Search;
using TotalRecall.Infrastructure.Storage;

const string SourceRevision = "a2630f671be9b12df8b8ac78df9d26f7053d2fa9";
const string AutoId = "doctor-auto-demotion";
const string ControlId = "doctor-vector-preserving-control";

var stopwatch = Stopwatch.StartNew();
var dbPath = args.Length == 1 ? args[0] : "/tmp/total-recall-restart-doctor.db";
if (File.Exists(dbPath))
{
    throw new InvalidOperationException("doctor database must not already exist");
}

var embedding = UnitVector(0);
var controlEmbedder = new UnitEmbedder();
int preRestartAutoWarm;
int preRestartAutoWarmVectors;
int preRestartControlWarm;
int preRestartControlWarmVectors;
int compacted;

using (var store = new SqliteStore(dbPath))
{
    store.InsertWithEmbedding(
        Tier.Hot,
        ContentType.Memory,
        new InsertEntryOpts(
            Content: "automatic demotion restart canary",
            MetadataJson: "{\"source_event_ids\":[\"doctor-write-auto\"]}",
            Id: AutoId,
            Scope: "restart-doctor"),
        embedding);
    store.InsertWithEmbedding(
        Tier.Hot,
        ContentType.Memory,
        new InsertEntryOpts(
            Content: "vector preserving move control",
            MetadataJson: "{\"source_event_ids\":[\"doctor-write-control\"]}",
            Id: ControlId,
            Scope: "restart-doctor"),
        embedding);

    var vectorSearch = new VectorSearch(store.Connection);
    var controlEntry = store.Get(Tier.Hot, ContentType.Memory, ControlId)
        ?? throw new InvalidOperationException("control row missing before move");
    MoveHelpers.MoveAndReEmbed(
        store,
        vectorSearch,
        controlEmbedder,
        controlEntry,
        Tier.Hot,
        ContentType.Memory,
        Tier.Warm,
        ContentType.Memory);

    var futureMs = DateTimeOffset.UtcNow.AddYears(10).ToUnixTimeMilliseconds();
    var result = HotTierCompactor.Compact(
        store,
        sessionId: "restart-doctor",
        nowMs: futureMs,
        warmThreshold: 0.99,
        decayConstantHours: 1.0,
        compactionLog: null);
    compacted = result.Compacted;

    preRestartAutoWarm = CountContent(store, "warm_memories", AutoId);
    preRestartAutoWarmVectors = CountVectors(store, "warm_memories", AutoId);
    preRestartControlWarm = CountContent(store, "warm_memories", ControlId);
    preRestartControlWarmVectors = CountVectors(store, "warm_memories", ControlId);
}

int postRestartAutoWarm;
int postRestartAutoWarmVectors;
int postRestartControlWarm;
int postRestartControlWarmVectors;
using (var reopened = new SqliteStore(dbPath))
{
    postRestartAutoWarm = CountContent(reopened, "warm_memories", AutoId);
    postRestartAutoWarmVectors = CountVectors(reopened, "warm_memories", AutoId);
    postRestartControlWarm = CountContent(reopened, "warm_memories", ControlId);
    postRestartControlWarmVectors = CountVectors(reopened, "warm_memories", ControlId);
}

stopwatch.Stop();
var gates = new SortedDictionary<string, bool>
{
    ["automatic_compactor_moved_exactly_one_row"] = compacted == 1,
    ["automatic_row_present_before_restart"] = preRestartAutoWarm == 1,
    ["automatic_row_vector_missing_before_restart"] = preRestartAutoWarmVectors == 0,
    ["automatic_row_deleted_by_restart_cleanup"] = postRestartAutoWarm == 0,
    ["manual_vector_preserving_control_present_before_restart"] =
        preRestartControlWarm == 1 && preRestartControlWarmVectors == 1,
    ["manual_vector_preserving_control_survives_restart"] =
        postRestartControlWarm == 1 && postRestartControlWarmVectors == 1,
};
var defectReproduced = gates.Values.All(value => value);
var report = new
{
    schema_version = 1,
    doctor = "total-recall-native-auto-demotion-restart-v1",
    source_revision = SourceRevision,
    status = defectReproduced
        ? "BLOCKED_NATIVE_RESTART_DEFECT_REPRODUCED"
        : "INCONCLUSIVE_NATIVE_BEHAVIOR_DRIFT",
    scientific_result = false,
    publication_ready = false,
    expected_negative_finding = true,
    automatic_transition = new
    {
        id = AutoId,
        pre_restart_content_rows = preRestartAutoWarm,
        pre_restart_vector_rows = preRestartAutoWarmVectors,
        post_restart_content_rows = postRestartAutoWarm,
        post_restart_vector_rows = postRestartAutoWarmVectors,
    },
    vector_preserving_control = new
    {
        id = ControlId,
        pre_restart_content_rows = preRestartControlWarm,
        pre_restart_vector_rows = preRestartControlWarmVectors,
        post_restart_content_rows = postRestartControlWarm,
        post_restart_vector_rows = postRestartControlWarmVectors,
    },
    gates,
    elapsed_ms = stopwatch.Elapsed.TotalMilliseconds,
};
Console.WriteLine(JsonSerializer.Serialize(report));
return defectReproduced ? 0 : 2;

static float[] UnitVector(int index)
{
    var vector = new float[384];
    vector[index] = 1.0f;
    return vector;
}

static int CountContent(SqliteStore store, string table, string id)
{
    using var command = store.Connection.CreateCommand();
    command.CommandText = $"SELECT COUNT(*) FROM {table} WHERE id = $id";
    command.Parameters.AddWithValue("$id", id);
    return Convert.ToInt32(command.ExecuteScalar());
}

static int CountVectors(SqliteStore store, string table, string id)
{
    using var command = store.Connection.CreateCommand();
    command.CommandText =
        $"SELECT COUNT(*) FROM {table}_vec v JOIN {table} c ON c.rowid = v.rowid WHERE c.id = $id";
    command.Parameters.AddWithValue("$id", id);
    return Convert.ToInt32(command.ExecuteScalar());
}

sealed class UnitEmbedder : IEmbedder
{
    public EmbedderDescriptor Descriptor { get; } =
        new(
            "cotcodec-doctor",
            "unit-vector-v1",
            "a2630f671be9b12df8b8ac78df9d26f7053d2fa9",
            384);

    public float[] Embed(string text) => UnitVector(0);

    private static float[] UnitVector(int index)
    {
        var vector = new float[384];
        vector[index] = 1.0f;
        return vector;
    }
}
