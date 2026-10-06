# CHANGELOG


## Unreleased

### Documentation

- Focus README on cy quickstart and Ultralytics migration
  ([`952ba62`](https://github.com/BuckanovNikita/clearml-yolo/commit/952ba62686900582f9ea71f9afd49cdb71f5253e))

- Record native FiftyOne evaluation release acceptance
  ([`ae1455c`](https://github.com/BuckanovNikita/clearml-yolo/commit/ae1455cc6d90d7f5eef5793181207593f6a2bb72))


## v0.16.0 (2026-10-06)

### Documentation

- Record evaluation publication release acceptance
  ([`d2ef6c1`](https://github.com/BuckanovNikita/clearml-yolo/commit/d2ef6c1ccfa43367e3fa791f5d00d31934f3f1b4))

### Features

- Publish native FiftyOne evaluation results and reports
  ([`60ab70b`](https://github.com/BuckanovNikita/clearml-yolo/commit/60ab70bf90fffab7747f0f53ab2e0e67ac08b764))


## v0.15.0 (2026-10-05)

### Features

- Publish complete evaluation evidence and interactive plots
  ([`0946121`](https://github.com/BuckanovNikita/clearml-yolo/commit/0946121fd91edecaf873df1a074f8146e46d0480))


## v0.14.4 (2026-10-05)

### Bug Fixes

- **metrics**: Warn and drop invalid prediction geometry
  ([`6cab994`](https://github.com/BuckanovNikita/clearml-yolo/commit/6cab9943da31c0f16be4398df91812be0db6717b))


## v0.14.3 (2026-10-05)

### Bug Fixes

- **compare**: Restore legacy ClearML artifact recovery
  ([`db33015`](https://github.com/BuckanovNikita/clearml-yolo/commit/db33015eb1b5d88050ce6e592002e3abc0b14bd7))


## v0.14.2 (2026-10-05)

### Bug Fixes

- **reports**: Retain metrics for new and deleted classes
  ([`b535aa8`](https://github.com/BuckanovNikita/clearml-yolo/commit/b535aa804bcb40f2b8cb05b9fb42fd874a4df4ee))


## v0.14.1 (2026-10-05)

### Bug Fixes

- **deps**: Require current metrics and report releases
  ([`7af1db6`](https://github.com/BuckanovNikita/clearml-yolo/commit/7af1db6cf19b8d62d5b8529e74169861afe76c81))


## v0.14.0 (2026-10-05)

### Bug Fixes

- Resolve reviewed tracking evaluation and queue defects
  ([`347344d`](https://github.com/BuckanovNikita/clearml-yolo/commit/347344d875013ba11ff4dea89e3a1789c65631c2))

### Documentation

- Use Sol orchestration and refresh GPU changelog
  ([`c7b77b8`](https://github.com/BuckanovNikita/clearml-yolo/commit/c7b77b83abc9b84c7ea21382b97d02e8d795aba4))

### Features

- **gpu**: Add user-wide FIFO experiment queue
  ([`6a55413`](https://github.com/BuckanovNikita/clearml-yolo/commit/6a55413a83c4542bc0721774ad588a22fbddca8f))

### Refactoring

- Remove legacy compatibility paths
  ([`4ca463f`](https://github.com/BuckanovNikita/clearml-yolo/commit/4ca463fc0f3e44cbdf9099f4a46175eca3b984a9))

### Breaking Changes

- Native-only training, historical checkpoint/threshold recovery, comparison overlays and legacy
  cache aliases are no longer supported.


## v0.13.2 (2026-10-02)

### Bug Fixes

- **clearml**: Restore task console logs
  ([`063b670`](https://github.com/BuckanovNikita/clearml-yolo/commit/063b670e3ecb0ee9dca9acaffa83244f40eb76e2))

- **publishing**: Keep visualization failures nonfatal
  ([`772e508`](https://github.com/BuckanovNikita/clearml-yolo/commit/772e50872016b5c84a35379d5da8c1f87a953380))


## v0.13.1 (2026-10-02)

### Bug Fixes

- Narrow workspace cache ownership
  ([`1e4b8db`](https://github.com/BuckanovNikita/clearml-yolo/commit/1e4b8dbc6add0c181067b82112bcf968b9a6a0a8))


## v0.13.0 (2026-10-01)

### Features

- Contain workspace writes and export evaluation evidence as CSV
  ([`eb7fdc6`](https://github.com/BuckanovNikita/clearml-yolo/commit/eb7fdc6b5ba09dadae5bdb12f82745769c25eb1d))

### Testing

- Consolidate redundant regression tests
  ([`bedc3af`](https://github.com/BuckanovNikita/clearml-yolo/commit/bedc3afa0d341e8fbdc520e01f4b0075b3d9f1f4))


## v0.12.0 (2026-09-30)

### Features

- **release**: Generate changelog in commit hooks and releases
  ([`2372b9a`](https://github.com/BuckanovNikita/clearml-yolo/commit/2372b9a558b3fa30a4515ce580ddd4956a5352b1))


## v0.11.0 (2026-09-30)

### Documentation

- Record resolved config upload verification and release
  ([`7f59526`](https://github.com/BuckanovNikita/clearml-yolo/commit/7f5952683fd011517e4d14c858c64f1a54190555))

### Features

- **tracking**: Stream native ClearML training progress
  ([`d96263c`](https://github.com/BuckanovNikita/clearml-yolo/commit/d96263c2444f6d69bd5e862a7acd1c0f01f6061f))


## v0.10.0 (2026-09-30)

### Features

- **config**: Resolve configuration files before ClearML upload
  ([`6aefaa3`](https://github.com/BuckanovNikita/clearml-yolo/commit/6aefaa354e2f20ef05e3d62b7901399548045133))


## v0.9.0 (2026-09-29)

### Features

- **tracking**: Reuse datasets and publish native ClearML models
  ([`589dc4a`](https://github.com/BuckanovNikita/clearml-yolo/commit/589dc4a563e8a767a3cf9b675df66820b0a3c83b))

### Breaking Changes

- **tracking**: Downloadable artifacts now follow the canonical CSV/XLSX inventory; best.pt is
  published as a native ClearML Output Model.


## v0.8.0 (2026-09-29)

### Features

- **config**: Derive task outputs and evaluate all dataset splits
  ([`5cbd93a`](https://github.com/BuckanovNikita/clearml-yolo/commit/5cbd93a07dd598cde788492e41455ff681a6e971))


## v0.7.0 (2026-09-29)

### Features

- **publishing**: Integrate default-enabled FiftyOne review layer
  ([`63fd899`](https://github.com/BuckanovNikita/clearml-yolo/commit/63fd89940303402af3fcd957dcd3cfabb5eea795))


## v0.6.0 (2026-09-29)

### Features

- **config**: Make detection settings explicit across native stages
  ([`a04e17e`](https://github.com/BuckanovNikita/clearml-yolo/commit/a04e17ee466d1bb69fdb2ca01b6ae394e6432a08))

### Breaking Changes

- **config**: Regenerate sparse native configuration examples. Default imgsz is 960, compile and nms
  are enabled, and incomplete native execution mappings are rejected.


## v0.5.0 (2026-09-29)

### Documentation

- Reconcile Spec Kit records with current implementation
  ([`0cdd8d1`](https://github.com/BuckanovNikita/clearml-yolo/commit/0cdd8d1feb7a585693180d9aba8798c7554cca5a))

- Record release GPU verification
  ([`cefcb8c`](https://github.com/BuckanovNikita/clearml-yolo/commit/cefcb8ce70a0f60dedfd4baf9a8d51f694c6204e))

### Features

- **training**: Train from ground-truth CSV with local NDJSON and flat datasets
  ([`ef7c6d9`](https://github.com/BuckanovNikita/clearml-yolo/commit/ef7c6d9d4118431a4716dc40ae9372960b664f72))


## v0.4.0 (2026-09-28)

### Documentation

- Record verified 0.3.0 publication
  ([`9f0475c`](https://github.com/BuckanovNikita/clearml-yolo/commit/9f0475c7815331bebd1b724a61e289766001a3af))

### Features

- **config**: Adopt native Ultralytics Hydra groups
  ([`23f8645`](https://github.com/BuckanovNikita/clearml-yolo/commit/23f864510abe0dc5a8d90546954f7e1dc670577d))

- **release**: Automate local semantic version tags
  ([`17cd5d5`](https://github.com/BuckanovNikita/clearml-yolo/commit/17cd5d5b6f4e0596302393b9ba4539b95529af03))


## v0.3.0 (2026-09-28)

### Bug Fixes

- Refuse a cfg file that is not a set of parameters
  ([`ac12bb6`](https://github.com/BuckanovNikita/clearml-yolo/commit/ac12bb6a19933145ba74cbc264c64e12d53f8bfd))

### Chores

- Finalize environment cleanup and metrics update
  ([`a5c80eb`](https://github.com/BuckanovNikita/clearml-yolo/commit/a5c80ebf04298299b588bb11fcee8110c7dad8cf))

- Upgrade ultralytics to 8.4.126 and re-sync the parameter files
  ([`12bd025`](https://github.com/BuckanovNikita/clearml-yolo/commit/12bd02567c9400a54b04886606b0972d7b7052c2))

### Documentation

- Describe the ClearML stand as the agents' target and the run-tag conventions
  ([`bae3454`](https://github.com/BuckanovNikita/clearml-yolo/commit/bae34547ac01a458120789d9bb47c46c9d29971e))

- Say that a run names its ultralytics file by path
  ([`988bb3e`](https://github.com/BuckanovNikita/clearml-yolo/commit/988bb3e4e5c8e8423d22a35ce8c3dc1e9b7b1ed9))

- **skills**: Clarify ClearML run contracts
  ([`ee512de`](https://github.com/BuckanovNikita/clearml-yolo/commit/ee512de50e1721c2ffab9ef6dbeaacb59d8d4a53))

### Features

- Deliver clearml-yolo 0.3.0 workflow
  ([`93ef462`](https://github.com/BuckanovNikita/clearml-yolo/commit/93ef462faac0a5929e4b48d64730c3bf53d110be))

- Keep the albumentations pipeline in the ClearML experiment
  ([`c81a696`](https://github.com/BuckanovNikita/clearml-yolo/commit/c81a6962214946df638a66e7a2e810c9817e1e3a))

- Load a custom albumentations pipeline from JSON
  ([`ddfc332`](https://github.com/BuckanovNikita/clearml-yolo/commit/ddfc33252582947d6592cb3e76b18471fe21445a))

- Name an ultralytics file by path instead of mounting a group
  ([`12511bd`](https://github.com/BuckanovNikita/clearml-yolo/commit/12511bd425cdc75ff24321d2cecab5995551eaee))

- Restore config examples and prepare 0.3.0 release
  ([`f52bcb0`](https://github.com/BuckanovNikita/clearml-yolo/commit/f52bcb09e9c2ff5da183e9edfc4388e660fc20c7))

- **agent**: Source the ClearML stand identity and mint a run tag for agent runs
  ([`f961ad6`](https://github.com/BuckanovNikita/clearml-yolo/commit/f961ad6b3d5ef12702fa460b236decf5ab06b22f))

- **cy**: Honour a queue wait deadline and derive the ClearML project from the run tag
  ([`d695fff`](https://github.com/BuckanovNikita/clearml-yolo/commit/d695fff0029ce825f5716707737ad30cc8b081d2))

### Testing

- **pipeline**: Write the ground truth the baseline check runs behind
  ([`f2730a1`](https://github.com/BuckanovNikita/clearml-yolo/commit/f2730a1ea070c4cb504afcb58ac235c942ada8c5))


## v0.2.0 (2026-08-19)

### Bug Fixes

- Detect GPU occupancy on WSL, where NVML names nobody
  ([`6b82a3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/6b82a3b7b75b0e845be45238e859f70c50a22f8e))

- Hand one card to one run, and give every run its own folder
  ([`7ef1c10`](https://github.com/BuckanovNikita/clearml-yolo/commit/7ef1c10ab4d633d4b9535aef24167bdb5c5247da))

- Harden the ClearML comparison report against odd frames
  ([#6](https://github.com/BuckanovNikita/clearml-yolo/pull/6),
  [`567cb3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/567cb3b2b85b0c9544b176fc6c5d9a4d49d16dc7))

- Honour a named device at every stage, and name the precision outright
  ([`bd41291`](https://github.com/BuckanovNikita/clearml-yolo/commit/bd41291abb90dd740205d4af564fe9a309c8c9a5))

- Keep p-values exact and reject drifting excluded columns
  ([#2](https://github.com/BuckanovNikita/clearml-yolo/pull/2),
  [`b1c1b0d`](https://github.com/BuckanovNikita/clearml-yolo/commit/b1c1b0d8d2a0e5c5035c556784f4a59ad99ec13d))

- Name the exclusion reasons and the pooled verdict honestly
  ([`288afa8`](https://github.com/BuckanovNikita/clearml-yolo/commit/288afa8e8fa06e406f5a64b2f4b567851c9c1d80))

- Never let a missing methodology value render as nan
  ([#2](https://github.com/BuckanovNikita/clearml-yolo/pull/2),
  [`b1c1b0d`](https://github.com/BuckanovNikita/clearml-yolo/commit/b1c1b0d8d2a0e5c5035c556784f4a59ad99ec13d))

- Read the pinned comparison contract, and count hypotheses not classes
  ([#6](https://github.com/BuckanovNikita/clearml-yolo/pull/6),
  [`567cb3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/567cb3b2b85b0c9544b176fc6c5d9a4d49d16dc7))

- Refuse a run that cannot finish, before it trains for an hour
  ([`f63f4a7`](https://github.com/BuckanovNikita/clearml-yolo/commit/f63f4a71e575def97c0fbda6d293634d7caba9ca))

- Reject a named checkpoint a run is about to train over
  ([`bb44fda`](https://github.com/BuckanovNikita/clearml-yolo/commit/bb44fda4c47325a15041feea14df67bb9927528f))

- Reject ground truth a name collision would silently merge
  ([#5](https://github.com/BuckanovNikita/clearml-yolo/pull/5),
  [`8221d23`](https://github.com/BuckanovNikita/clearml-yolo/commit/8221d23c7fae3d20d5a6c6f3a51eb57b9153f6fa))

- Reject index labels that cannot carry the match-record join
  ([#4](https://github.com/BuckanovNikita/clearml-yolo/pull/4),
  [`d4402d6`](https://github.com/BuckanovNikita/clearml-yolo/commit/d4402d6097fb5594f5210313c3172064418a4b85))

- Reject missing detection flags instead of reading them as detected
  ([#1](https://github.com/BuckanovNikita/clearml-yolo/pull/1),
  [`5bef976`](https://github.com/BuckanovNikita/clearml-yolo/commit/5bef97682d3406a0aedc88deded62298d61716f8))

- Resolve stage sub-configs to plain Python in the pipeline
  ([`d889f1c`](https://github.com/BuckanovNikita/clearml-yolo/commit/d889f1c6f90a736fe878b339d668c9fe4f63f142))

- Say so when NVML refuses to name the processes on a card
  ([`1d085ea`](https://github.com/BuckanovNikita/clearml-yolo/commit/1d085eaeb455f9e60cbafac22e0e69c9c394e46b))

- Size the batch on the card a stage was handed, not only on one it found
  ([`94a084e`](https://github.com/BuckanovNikita/clearml-yolo/commit/94a084eb25f7af4e090118e772b2ce5a59c9c549))

- Speed inference up by decoding off the main thread, not by batching
  ([`e2a70ff`](https://github.com/BuckanovNikita/clearml-yolo/commit/e2a70ffcc5ea334401a10a03cfde244601685474))

- Stop Hydra's defaults list reaching a task as a keyword argument
  ([`5cac098`](https://github.com/BuckanovNikita/clearml-yolo/commit/5cac098326e77df12149dd6bfb09ba0228cad7d8))

- Stop the comparison from resolving both sides to one model
  ([`c2f685e`](https://github.com/BuckanovNikita/clearml-yolo/commit/c2f685ea17a5cf5cc09850f7b9d3953f1e71fdb1))

- Stop the comparison reusing another checkpoint's predictions
  ([`0269998`](https://github.com/BuckanovNikita/clearml-yolo/commit/0269998163861ff9be824b15b720d3d00ace01ec))

### Chores

- Drop the obsolete augmentation fixture from .gitignore
  ([`8550424`](https://github.com/BuckanovNikita/clearml-yolo/commit/8550424f35fbfe2d3cf4331fcfaa24da3da95f19))

- Hold the layering with import contracts, and tighten ruff and mypy
  ([`15636d1`](https://github.com/BuckanovNikita/clearml-yolo/commit/15636d1b2acc60a6cab755b3f15d3ccecbb56428))

- Release 0.2.0
  ([`6931e10`](https://github.com/BuckanovNikita/clearml-yolo/commit/6931e1043b40aabcfb4784e320642f37ffeec6f4))

### Documentation

- Anchor the drift-prone references this pass introduced
  ([`01e0f73`](https://github.com/BuckanovNikita/clearml-yolo/commit/01e0f73119fbbe6b49f3cdeb659eee8b444059b2))

- Describe the manifest source and what dropping the decode-ahead cost
  ([`10317e0`](https://github.com/BuckanovNikita/clearml-yolo/commit/10317e0b88e8ce9893ecd1baf09d6c5b630d1bf2))

- Describe the shared keys, the new artifact names and the decode-ahead
  ([`e7f84a6`](https://github.com/BuckanovNikita/clearml-yolo/commit/e7f84a6357cfc34a920dae593df56a652483492e))

- Describe the ultralytics parameter files and their null rule
  ([`cff2870`](https://github.com/BuckanovNikita/clearml-yolo/commit/cff2870d31c30a0de53550a6fbe0eba81f529403))

- Design ultralytics params as a config group of their own
  ([`6693ed4`](https://github.com/BuckanovNikita/clearml-yolo/commit/6693ed481ccbc73888eb478c7a5ed32c5d2518bb))

- Document waiting, the reserve, cy-compare and the config folder
  ([`a01ba3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/a01ba3b8db48a93c035c808154ab230b2b249a09))

- Drop the secure-shell pointer now that auto mode handles permissions
  ([`8cf8934`](https://github.com/BuckanovNikita/clearml-yolo/commit/8cf8934c8011f4493adf15e0b2202dfb59574e02))

- Hand each stage its shared values from code, not by interpolation
  ([`f178c52`](https://github.com/BuckanovNikita/clearml-yolo/commit/f178c528cfb6bda24628ddacd6914074b06da996))

- Make the commands run, and name where a first run breaks
  ([`daaa12d`](https://github.com/BuckanovNikita/clearml-yolo/commit/daaa12d991d93e61d5b9c38f1c5ed89aaf0d640a))

- Name the prod model, the resolution and the split check once
  ([`5941330`](https://github.com/BuckanovNikita/clearml-yolo/commit/59413301f0c1c0e95a09f62eb5d8a8226642510f))

- Name what a run produces, not how much of it there was
  ([`da2b2a8`](https://github.com/BuckanovNikita/clearml-yolo/commit/da2b2a823db195542569d25f5d1a9c046b6ccc05))

- Pin the end state of a ClearML run to what one actually produced
  ([`5482121`](https://github.com/BuckanovNikita/clearml-yolo/commit/5482121e2e71619d68c449a4a2a6c6bfbd980ed6))

- Pin the predict confidence the key-union test cannot see
  ([`d34ff98`](https://github.com/BuckanovNikita/clearml-yolo/commit/d34ff983943a7f1da8f6e539d84356fa4a9093d7))

- Plan the move from interpolations to values handed over in code
  ([`777063e`](https://github.com/BuckanovNikita/clearml-yolo/commit/777063ef670ad19a4fc76b81ac92dc4bcb48abfb))

- Record what implementation changed about the design
  ([`c02082e`](https://github.com/BuckanovNikita/clearml-yolo/commit/c02082e6317079b5d9d05672c66b45baa94a200a))

- Say that compile and FP16 are on by default here, off upstream
  ([`2efe918`](https://github.com/BuckanovNikita/clearml-yolo/commit/2efe918bdce8aa4ec02853950f82dbb886d5c925))

- Say that the run hands each stage its shared values
  ([`22aa56b`](https://github.com/BuckanovNikita/clearml-yolo/commit/22aa56b5ac5c46f3ecb110e2c2800936669c96a9))

- Say that two plain runs split seven and one, not evenly
  ([`4d52fc9`](https://github.com/BuckanovNikita/clearml-yolo/commit/4d52fc9ca913c2540cf67b2355291e758cd2f9bf))

- Say what the full tests are here, and check the tools before trusting them
  ([`91cd97b`](https://github.com/BuckanovNikita/clearml-yolo/commit/91cd97b52dbd3d2b3aa2efb46d31102bdcb1a127))

- Say what the two card bounds mean and where force gets you
  ([`705ef6c`](https://github.com/BuckanovNikita/clearml-yolo/commit/705ef6c4169273311cffa710dfdeb8fde1a16933))

- Say where a run now refuses, and where it keeps the resolution it used
  ([`ff78c92`](https://github.com/BuckanovNikita/clearml-yolo/commit/ff78c92361af6a3e34556a3d6ed0b113a7b92be8))

- Say where the batch comes from and what it moves
  ([`ca3e5cb`](https://github.com/BuckanovNikita/clearml-yolo/commit/ca3e5cb4a0f4c708df512ad5739311205a295e73))

- Say which run a card and a folder belong to
  ([`a08c583`](https://github.com/BuckanovNikita/clearml-yolo/commit/a08c58392760337d494f6fb9fc6ecaeede72a088))

- Show the command-line form Hydra actually accepts
  ([`f7885e8`](https://github.com/BuckanovNikita/clearml-yolo/commit/f7885e83fd584135477e56d382e9ccd72c8546f2))

- Tell an old config folder's owner to re-dump it too
  ([`c6a9f9d`](https://github.com/BuckanovNikita/clearml-yolo/commit/c6a9f9d2fbf773dbba424dde47c15824c7e49ad0))

### Features

- Add significance tests for per-class model comparison
  ([#1](https://github.com/BuckanovNikita/clearml-yolo/pull/1),
  [`5bef976`](https://github.com/BuckanovNikita/clearml-yolo/commit/5bef97682d3406a0aedc88deded62298d61716f8))

- Bootstrap a confidence interval for the recall delta too
  ([#1](https://github.com/BuckanovNikita/clearml-yolo/pull/1),
  [`5bef976`](https://github.com/BuckanovNikita/clearml-yolo/commit/5bef97682d3406a0aedc88deded62298d61716f8))

- Build the digital-metrics ground truth from a YOLO dataset yaml
  ([#5](https://github.com/BuckanovNikita/clearml-yolo/pull/5),
  [`8221d23`](https://github.com/BuckanovNikita/clearml-yolo/commit/8221d23c7fae3d20d5a6c6f3a51eb57b9153f6fa))

- Give auto_gpu a floor, a ceiling and one batch
  ([`9fc9a32`](https://github.com/BuckanovNikita/clearml-yolo/commit/9fc9a32b14dd94905458e577ba1a00f8676f7cb1))

- Give every run its own folder, and a queue that arbitrates the cards
  ([`e211e88`](https://github.com/BuckanovNikita/clearml-yolo/commit/e211e8873be8c131f299d7bcdb92156ecdc1067d))

- Give the comparison, the ground truth and the defaults a way in
  ([`900f097`](https://github.com/BuckanovNikita/clearml-yolo/commit/900f0979094b7e35f13a266e5fc8b38c9a17d67b))

- Give ultralytics a parameter file of its own, with every key visible
  ([`44c3cd3`](https://github.com/BuckanovNikita/clearml-yolo/commit/44c3cd3bcc00717441207acb2ac7cdf7991c7f5e))

- Hydra-zen apps for YOLO training, metrics and model comparison
  ([`e4ec105`](https://github.com/BuckanovNikita/clearml-yolo/commit/e4ec105b98cb531f49f68aa9bf64fa13b761a5fe))

- Make the comparison the last stage of the pipeline
  ([`3610720`](https://github.com/BuckanovNikita/clearml-yolo/commit/36107204703c7d4ca08156c888b0021369507034))

- Minimal model-comparison workbook ([#2](https://github.com/BuckanovNikita/clearml-yolo/pull/2),
  [`b1c1b0d`](https://github.com/BuckanovNikita/clearml-yolo/commit/b1c1b0d8d2a0e5c5035c556784f4a59ad99ec13d))

- Name each shared value once, batch inference, show progress
  ([`f0e428c`](https://github.com/BuckanovNikita/clearml-yolo/commit/f0e428c8f0e130d95630b109944d77639b87e628))

- Patch ultralytics to recognise every albumentations transform type
  ([`6e048c5`](https://github.com/BuckanovNikita/clearml-yolo/commit/6e048c546658fafa0bacd9299385e109966e5e23))

- Publish the model comparison to ClearML readably
  ([#6](https://github.com/BuckanovNikita/clearml-yolo/pull/6),
  [`567cb3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/567cb3b2b85b0c9544b176fc6c5d9a4d49d16dc7))

- Re-infer the previous model on the current test split
  ([#3](https://github.com/BuckanovNikita/clearml-yolo/pull/3),
  [`f088bfc`](https://github.com/BuckanovNikita/clearml-yolo/commit/f088bfc7b71e2bfbe0ea785c9032f4079c84f646))

- Readable ClearML reporting for the model comparison
  ([#6](https://github.com/BuckanovNikita/clearml-yolo/pull/6),
  [`567cb3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/567cb3b2b85b0c9544b176fc6c5d9a4d49d16dc7))

- Reconcile custom albumentations with ultralytics' own augmentations
  ([`d7366e3`](https://github.com/BuckanovNikita/clearml-yolo/commit/d7366e37637864585092529815a7a0a5f22c0fdb))

- Refuse the resolution a run cannot honour, and record the one it used
  ([`bcfb53f`](https://github.com/BuckanovNikita/clearml-yolo/commit/bcfb53fd1e7fa7b2cf9898be27ea2fb6fad5363c))

- Run inference from a ClearML task, on a device it waited for
  ([`fe68cda`](https://github.com/BuckanovNikita/clearml-yolo/commit/fe68cdaaed8e74cb4dd5984afa7244bab9eef0cb))

- Score a split at frozen per-class thresholds
  ([#4](https://github.com/BuckanovNikita/clearml-yolo/pull/4),
  [`d4402d6`](https://github.com/BuckanovNikita/clearml-yolo/commit/d4402d6097fb5594f5210313c3172064418a4b85))

- Significance tests for per-class model comparison
  ([#1](https://github.com/BuckanovNikita/clearml-yolo/pull/1),
  [`5bef976`](https://github.com/BuckanovNikita/clearml-yolo/commit/5bef97682d3406a0aedc88deded62298d61716f8))

- Size the batch from the model and the card, once, for every stage
  ([`08d9db1`](https://github.com/BuckanovNikita/clearml-yolo/commit/08d9db1c0b15f399e9932d43a17e5bd6221219b6))

- Train in mixed precision with torch.compile, and drop the deprecated half flag
  ([`5fec9d6`](https://github.com/BuckanovNikita/clearml-yolo/commit/5fec9d6464628241c7acf46a02fe26b3df9dace4))

- Turn on half precision and torch.compile on CUDA by default
  ([`1792e84`](https://github.com/BuckanovNikita/clearml-yolo/commit/1792e840bb0207a451a049fd29b0100747ca5e8c))

- Wait for GPUs and reserve one for other runs' inference
  ([`cfd669c`](https://github.com/BuckanovNikita/clearml-yolo/commit/cfd669c21f8ed1d571ec6c8c083b64164e93d5b0))

- Write the minimal model-comparison workbook
  ([#2](https://github.com/BuckanovNikita/clearml-yolo/pull/2),
  [`b1c1b0d`](https://github.com/BuckanovNikita/clearml-yolo/commit/b1c1b0d8d2a0e5c5035c556784f4a59ad99ec13d))

### Refactoring

- Find both sides of the report with one lookup
  ([`963bdfc`](https://github.com/BuckanovNikita/clearml-yolo/commit/963bdfc577ce4b883281c28a533d8b59ce28bd9a))

- Forward each stage's config whole, and name a baseline once per run
  ([`af8d8c5`](https://github.com/BuckanovNikita/clearml-yolo/commit/af8d8c51829747cd77311151401585ac9106f254))

- Hand each stage the values the run decided
  ([`0dc3b59`](https://github.com/BuckanovNikita/clearml-yolo/commit/0dc3b59aaa033eaa349b6b15f88cdc32b343fe57))

- Lead the headline value names with the direction
  ([#6](https://github.com/BuckanovNikita/clearml-yolo/pull/6),
  [`567cb3b`](https://github.com/BuckanovNikita/clearml-yolo/commit/567cb3b2b85b0c9544b176fc6c5d9a4d49d16dc7))

- Let a stage declare only what it alone decides
  ([`c39ee7a`](https://github.com/BuckanovNikita/clearml-yolo/commit/c39ee7a6db9f0beb974858af021f8c737494e417))

- Let ultralytics do the batching, decoding and path attribution
  ([`ea08f6b`](https://github.com/BuckanovNikita/clearml-yolo/commit/ea08f6b6a1bb46513e13cfcf2ba68f21bde7e3b6))

- Name the run layout where training decides it
  ([`c61adf4`](https://github.com/BuckanovNikita/clearml-yolo/commit/c61adf49760df358a613f796e1f26886ef0d0741))

### Testing

- Keep the GPU suite off the real machine
  ([`fea116f`](https://github.com/BuckanovNikita/clearml-yolo/commit/fea116f9176f1040dba160a711031032717b4261))

- Keep the mirrored bootstrap case off the p-value floor
  ([#1](https://github.com/BuckanovNikita/clearml-yolo/pull/1),
  [`5bef976`](https://github.com/BuckanovNikita/clearml-yolo/commit/5bef97682d3406a0aedc88deded62298d61716f8))

- Name the mirrored bootstrap frames by their strength
  ([#1](https://github.com/BuckanovNikita/clearml-yolo/pull/1),
  [`5bef976`](https://github.com/BuckanovNikita/clearml-yolo/commit/5bef97682d3406a0aedc88deded62298d61716f8))

- Pin each rung of the batch ladder and the resolution it runs at
  ([`462dd5a`](https://github.com/BuckanovNikita/clearml-yolo/commit/462dd5a970187c185911ae85ca97a97d37b14e5e))

- Pin the baseline with the report switched off
  ([`9fea658`](https://github.com/BuckanovNikita/clearml-yolo/commit/9fea65855153d84b49a26b1ca199a4a176b279fd))

- Pin the iou_prior recall-denominator invariant
  ([#4](https://github.com/BuckanovNikita/clearml-yolo/pull/4),
  [`d4402d6`](https://github.com/BuckanovNikita/clearml-yolo/commit/d4402d6097fb5594f5210313c3172064418a4b85))

- Pin the run directory the file and the code both name
  ([`cf08ef6`](https://github.com/BuckanovNikita/clearml-yolo/commit/cf08ef683ecc50f560d74d701c1d247ac2794399))

- Pin the shared config keys and the batched predictor
  ([`97ef1d5`](https://github.com/BuckanovNikita/clearml-yolo/commit/97ef1d5ec27ea08cd49ced2d3606bf7dcf751807))

- Pin the split, the settling pass, the release and the seizure
  ([`c6122ef`](https://github.com/BuckanovNikita/clearml-yolo/commit/c6122ef0fc24cc1ba44dfed859e04282e38b9a4c))

- Pin the two gaps the parity check let through
  ([`797f094`](https://github.com/BuckanovNikita/clearml-yolo/commit/797f094adc657c8a0a4d6c55201490c9e6357472))
