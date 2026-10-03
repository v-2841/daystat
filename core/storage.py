from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class HashedStaticFilesStorage(ManifestStaticFilesStorage):
    """Static files with a content hash in their names.

    Scripts keep their source map links as they are: the vendor bundles
    point at .map files that are not shipped, and a missing one fails
    collectstatic, which entrypoint.sh runs before the app starts.
    """

    patterns = tuple(
        (extension, rules)
        for extension, rules in ManifestStaticFilesStorage.patterns
        if extension != '*.js'
    )
