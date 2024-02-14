import pytest

from pyreduce import reduce


def test_main(instrument, target, night, mode, input_dir, output_dir):
    output = reduce.main(
        instrument,
        target,
        night,
        mode,
        base_dir_template="",
        input_dir_template=input_dir,
        output_dir_template=output_dir,
        steps=[],
    )

    assert isinstance(output, list)
    assert len(output) >= 1
    assert "config" in output[0].keys()
    assert "files" in output[0].keys()

    # Test default options
    # Just not find anything
    output = reduce.main(instrument, target, night, steps=[])


@pytest.mark.skip
def test_run_all(instrument, target, night, mode, input_dir, output_dir, order_range):
    output = reduce.main(
        instrument,
        target,
        night,
        mode,
        steps="all",
        base_dir_template="",
        input_dir_template=input_dir,
        output_dir_template=output_dir,
        order_range=order_range,
    )


@pytest.mark.skip
def test_load_all(instrument, target, night, mode, input_dir, output_dir, order_range):
    output = reduce.main(
        instrument,
        target,
        night,
        mode,
        steps=["finalize"],
        base_dir_template="",
        input_dir_template=input_dir,
        output_dir_template=output_dir,
        order_range=order_range,
    )


def test_step_abstract(step_args):
    step = reduce.Step(*step_args, **{"plot": False})

    assert isinstance(step.dependsOn, list)
    assert isinstance(step.loadDependsOn, list)
    assert isinstance(step.prefix, str)
    assert isinstance(step.output_dir_template, str)

    with pytest.raises(NotImplementedError):
        step.load()

    with pytest.raises(NotImplementedError):
        step.run([])

    with pytest.raises(NotImplementedError):
        step.save()
