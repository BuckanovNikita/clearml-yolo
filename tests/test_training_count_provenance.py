"""Training count provenance follows prepared training rows, never evaluation rows."""

from pathlib import Path

from clearml_yolo.adapters.integrations.training import training_population_counts


def test_counts_preserve_lexical_labels_and_ignore_other_splits(tmp_path: Path) -> None:
    source = tmp_path / "ground_truth.csv"
    source.write_text(
        "instance_label,split\n0001,train\n0001,train\nNA,train\ncat,test\ncat,val\n,train\n",
        encoding="utf-8",
    )
    assert training_population_counts(source) == {"0001": 2, "NA": 1}
