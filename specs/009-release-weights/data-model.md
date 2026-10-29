# Data model

The [manifest contract](contracts/manifest.md) defines release, archive, asset and native Hub snapshot records. `AssetSpec.identity` links installed discovery to a snapshot without changing original source provenance. Manifest and archive hashes identify immutable content; preparation receipts additionally bind the manifest identity. Archive files are local persistent cache entries, while native files retain existing SDK-selected destinations.
