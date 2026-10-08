# Research decisions

Existing ten import contracts pass but allow omitted-module SDK imports and indirect publication tracking. In-memory tightening proved coverage fixes without application changes. Full redesign additionally requires explicit ports and removal of the app helper cycle. Pandera 0.34.1 supports Python >=3.10 and its pandas extra requires pandas>=2.1.1/numpy>=1.24.4. Installed versions already meet those floors; dependency resolution remains a verification step. Clean import/YAML cutover explicitly approved.

Digital-metrics Metrics is a public Pydantic model; adapters can translate project records and reconstruct reporting inputs without upstream modification. get_dashboards writes directories/plots even when save_to_excel=False, so it must remain in rendering adapters.
