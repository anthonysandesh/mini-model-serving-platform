from mmsp.deploy.canary import DeploymentState, choose_version


def test_choose_version_canary_wins() -> None:
    state = DeploymentState(model_name="m", prod_version=1, canary_version=2, canary_weight=100)
    assert choose_version(state) == 2


def test_choose_version_prod_when_zero_weight() -> None:
    state = DeploymentState(model_name="m", prod_version=1, canary_version=2, canary_weight=0)
    assert choose_version(state) == 1
