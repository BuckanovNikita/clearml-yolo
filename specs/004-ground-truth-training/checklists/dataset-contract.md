# Dataset Contract Checklist: Ground-Truth Training

**Purpose**: Review requirements before implementation.

**Created**: 2026-09-29

**Feature**: [spec.md](../spec.md)

**Review Ownership**: Reviewer-owned requirements-quality artifact; checked items mean
requirements are clear, not that implementation is complete.

## Input and Conversion

- [x] CHK001 Are required columns, pixel coordinates, image identity, and path resolution explicit? [FR-002, FR-003]
- [x] CHK002 Are recoverable invalid boxes distinguished from fatal structural errors, with exact count semantics? [FR-004, FR-019]
- [x] CHK003 Are background retention and the all-invalid training-set boundary specified? [FR-005, Edge Cases]
- [x] CHK004 Are both formats, the default, class mapping, and coordinate tolerance explicit? [FR-006–FR-010]

## Integration and Acceptance

- [x] CHK005 Are data override authority and unrelated native settings distinguished? [FR-011, FR-012]
- [x] CHK006 Are output ownership, artifact privacy, and failure lifecycle requirements complete? [FR-013–FR-015]
- [x] CHK007 Do evaluation and comparison explicitly consume cleaned annotations and frozen validation thresholds? [FR-016, FR-019]
- [x] CHK008 Are compatibility, skipped training, examples, and real execution acceptance defined? [FR-017, FR-018, SC-005]

## Notes

The implementation skill reads this gate without changing markers. Review each item
against the referenced specification before implementation.
