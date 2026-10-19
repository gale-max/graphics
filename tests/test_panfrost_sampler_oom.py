from pathlib import Path


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "mesa/upstream/src/gallium/drivers/panfrost/pan_cmdstream.c"
)


def test_sampler_state_allocation_failure_returns_null_before_dereference():
    source = SOURCE.read_text(encoding="utf-8")
    body = source.split("panfrost_create_sampler_state(", 1)[1].split(
        "/* Get pointers to the blend shaders", 1
    )[0]
    allocation = body.index("CALLOC_STRUCT(panfrost_sampler_state)")
    check = body.index("if (!so)", allocation)
    assert check < body.index("so->base = *cso", allocation)
    assert "return NULL;" in body[check : body.index("so->base = *cso", allocation)]
