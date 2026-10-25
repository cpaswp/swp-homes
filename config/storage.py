from whitenoise.storage import CompressedManifestStaticFilesStorage


class NonStrictCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Keep missing manifest entries from crashing template rendering in tests/dev.

    Production deployments should still run collectstatic so hashed assets are
    present in the manifest; strict=False provides a safe unhashed fallback.
    """
    manifest_strict = False
