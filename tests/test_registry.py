from pathlib import Path

from mmsp.registry.store import RegistryStore


def test_registry_register_and_promote(tmp_path: Path) -> None:
    artifact = tmp_path / "model.onnx"
    artifact.write_bytes(b"dummy")
    store = RegistryStore(tmp_path / "registry.json")
    mv = store.register("m", "onnx", str(artifact))
    assert mv.version == 1
    store.promote("m", mv.version, "prod")
    assert store.current_stage("m", "prod") == mv.version
