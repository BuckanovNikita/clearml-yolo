# Bug Fix: New and deleted class metrics

- Slug: new-deleted-class-metrics
- Fixed: 2026-10-05
- Assessment: [assessment](assessment.md)
- Status: applied

## Summary

Developer/business builders now retain independently eligible model data and align display rows over the class union. Statistical workbooks retain vocabulary differences and mark absent model data and untestable comparisons unavailable.

## Changes

| Area | Change |
| --- | --- |
| report-generator builders/calculators | Own-model means, coverage and business verdict inputs; union display; shared-class difference means |
| report-generator writers | NA for missing cells and verdict operands without comparison colors; population notes and exclusion provenance |
| comparison assembly/workbook | Union rows, missing unsupported counts/thresholds/metrics, unavailable verdicts, pooled tests and counts over identical shared eligible populations |
| ClearML presentation | No NaN pooled delta headlines; unavailable rows remain outside tested counts |
| dependency metadata | report-generator 0.1.2 requirement and local lock version; digital-metrics unchanged |

## Tests Added or Updated

Reopened-workbook tests cover shared/new/deleted/disjoint vocabularies, asymmetric filters, empty eligible populations, zeros versus missingness, differing IDs and metric columns, means/coverage, business denominators, NA and colors. Statistical tests cover pooled contamination, family membership, no comparable population and ClearML headlines. Parent real-builder integration reproduces and verifies cy-report behavior.

## Local Verification

Before implementation: six new report-generator workbook cases, five statistical cases and both parent real-builder cases failed for the reported behavior. Check commands and final results are recorded in test.md after final acceptance.

## Documentation Update

Updated report-generator README, parent README, current-contract index and CLI evaluation contract. Historical evidence and publication artifact names remain unchanged. No machine-specific guidance added to project documentation. Validate Markdown and links before acceptance.

## Deviations from Assessment

User clarified releases must publish Git version tags only, with no assets or registry publication. Follow this instruction for v0.1.2; no GitHub Release object or attachments are needed. Global personal instructions now persist this preference.

## Follow-ups

Parent checks and independent review completed; v0.1.2 tag published. See test.md for evidence and limitations. Parent changes remain uncommitted.
