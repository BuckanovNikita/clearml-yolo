# Model-weight redistribution evidence — 2026-10-29

This inventory records the upstream terms inspected for the initial independently
versioned weight snapshot. It is licence/provenance evidence, not proof of successful
publication or native loading. Preserve complete licence texts in the archive notices;
links in this document do not replace copies required with redistributed material.

## Catalogue inspected

The maintained bulk-preparation catalogue contains 60 selections, deduplicated to
55 weight requests and the pinned DEIMv2 source archive. Faster R-CNN and FCOS share
their five eligible pretrained backbones. DEIMv2 large/xlarge and both
`dinov3_small` selections remain excluded by preparation policy.

The YOLO requests are detection assets from `ultralytics/assets` release `v8.4.0`:

- `yolov3u.pt`, `yolov3-sppu.pt`, `yolov3-tinyu.pt`;
- `yolov5{n,s,m,l,x}u.pt` and `yolov5{n,s,m,l,x}6u.pt`;
- `yolov8{n,s,m,l,x}.pt`, `yolov9{t,s,m,c,e}.pt`, `yolov10{n,s,m,b,l,x}.pt`;
- `yolo11{n,s,m,l,x}.pt`, `yolo12{n,s,m,l,x}.pt`, `yolo26{n,s,m,l,x}.pt`.

Brace groups identify each listed filename expansion, not a different download format.
The packaged manifest records exact filenames, original URLs/revisions, member hashes
and sizes. Hub representations can use `model.safetensors` or `pytorch_model.bin`
instead of the original URL checkpoint filename; retain their real snapshot metadata.

## Licence and notice requirements

### Ultralytics detection weights

The [official assets repository](https://github.com/ultralytics/assets) identifies
pretrained model assets and offers AGPL-3.0 or Enterprise licensing. Its
[AGPL licence](https://raw.githubusercontent.com/ultralytics/assets/main/LICENSE)
permits redistribution subject to its notice and source obligations. The
[vendor licence explanation](https://www.ultralytics.com/license) expressly includes
trained models. This snapshot uses the public AGPL route, not an Enterprise grant.

Include the complete AGPL text, preserve copyright/licence notices and state whether
the checkpoint bytes were modified. Give clear corresponding-source directions next
to the downloadable archives, keeping that source available. Separate independent
assets remain an aggregate under section 5; do not imply a single permissive licence
for the tar collection. Model files and source links must remain traceable to their
upstream release and historical training implementation.

Read-only ZIP/pickle-opcode inspection, without executing checkpoint pickle, found
AGPL metadata in 39 of the 44 local checkpoints. YOLO12 files lacked detectable
top-level licence/version metadata; the assets repository's licence remains relevant.
Embedded versions vary: YOLOv3 `8.0.25`; YOLOv5 `8.0.22` and six-resolution variants
`8.0.49`; YOLOv8 `8.0.0.dev0`; YOLOv9 `8.2.31`/`8.1.23`/`8.3.21`; YOLOv10
`8.2.30`; YOLO11 `8.2.100`; YOLO26 `8.3.222`. Installed-loader source alone does
not establish exact historical training reproducibility. Retain the
[upstream source repository](https://github.com/ultralytics/ultralytics), applicable
historical references and original checkpoint metadata without claiming that gap closed.

### RF-DETR

Files: `rf-detr-nano.pth`, `rf-detr-small.pth`, `rf-detr-medium.pth` and
`rf-detr-large-2026.pth`. The
[pinned 1.11.2 README](https://raw.githubusercontent.com/roboflow/rf-detr/1.11.2/README.md)
explicitly lists Nano, Small, Medium and Large as Apache-2.0; these are not the
Plus/PML models. The
[licence](https://raw.githubusercontent.com/roboflow/rf-detr/1.11.2/LICENSE)
requires a copy with redistribution, retained applicable notices and prominent
change notices for modified files. No `NOTICE` file was found in that revision's
repository tree. Preserve Roboflow and DINOv2 provenance; do not extend this finding
to uninspected Plus sizes.

### DEIMv2 and distilled DINOv3 backbones

Files: `vitt_distill.pt`, `vittplus_distill.pt` and source archive
`1d2ca42171570c713e78fc6a766ec5104b7f4724.tar.gz`. The
[exact pinned DEIMv2 licence](https://raw.githubusercontent.com/Intellindust-AI-Lab/DEIMv2/1d2ca42171570c713e78fc6a766ec5104b7f4724/LICENSE.md)
explicitly covers source and model weights. It permits use and redistribution only
for non-commercial purposes; commercial use requires a separate licence. Include
the full licence, applicable copyright/attribution, modification status and the
non-commercial limitation. Do not represent these files as commercially unrestricted.
Third-party material retains its own terms.

The [pinned backbone preparation guide](https://github.com/Intellindust-AI-Lab/DEIMv2/blob/1d2ca42171570c713e78fc6a766ec5104b7f4724/README.md#23-backbone-preparation)
identifies Tiny/Tiny+ as distilled from DINOv3-S. Include the
[DINOv3 agreement](https://raw.githubusercontent.com/facebookresearch/dinov3/main/LICENSE.md)
alongside the DEIM notice. That agreement allows redistribution and derivatives with
an agreement copy, while retaining its use restrictions. Its existence is not a
blanket redistribution ban; it also does not remove DEIM's non-commercial condition.

### Shared Torchvision/timm backbones

| Native request | Inspected terms and notices |
| --- | --- |
| `resnet50-11ad3fa6.pth`, `resnet101-cd907fc2.pth` | Preserve [Torchvision BSD-3-Clause](https://raw.githubusercontent.com/pytorch/vision/main/LICENSE), including copyright, conditions and disclaimer. The [upstream pretrained-model qualification](https://github.com/pytorch/vision#pre-trained-model-license) says dataset-derived terms may apply; no separate restriction for these two standard ResNet checkpoints was found. This is not a blanket BSD-only conclusion for all Torchvision weights. |
| `convnext_tiny.fb_in22k_ft_in1k` / original `convnext_tiny_22k_1k_224.pth` | The [native timm model card](https://huggingface.co/timm/convnext_tiny.fb_in22k_ft_in1k) declares Apache-2.0; the [original Meta repository licence](https://raw.githubusercontent.com/facebookresearch/ConvNeXt/main/LICENSE) is MIT. Preserve both texts, the Meta copyright and model-card/source provenance. |
| `swin_tiny_patch4_window7_224.ms_in1k` / original `swin_tiny_patch4_window7_224.pth` | The [model card](https://huggingface.co/timm/swin_tiny_patch4_window7_224.ms_in1k) and [original Microsoft licence](https://raw.githubusercontent.com/microsoft/Swin-Transformer/main/LICENSE) use MIT. Include the full copyright, permission and disclaimer notice. |
| `vit_small_patch14_dinov2.lvd142m` / original `dinov2_vits14_pretrain.pth` | The [model card](https://huggingface.co/timm/vit_small_patch14_dinov2.lvd142m) declares Apache-2.0; [upstream](https://github.com/facebookresearch/dinov2#license) explicitly applies it to code and weights. Include the [licence](https://raw.githubusercontent.com/facebookresearch/dinov2/main/LICENSE), applicable attribution and modification notices. |

## Publication acceptance

The complete licence texts, retained upstream source/model-card provenance and
per-file manifest belong with the snapshot. Identify the DEIM non-commercial terms
in release notes as well as in archive notices. Verify actual hosted bytes and
offline native restoration separately, following the
[weight release procedure](../../docs/development.md#model-weight-releases).
Ordinary code-release tags neither republish weights nor authorize project
distribution or registry uploads.
