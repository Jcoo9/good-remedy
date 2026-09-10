# Good Remedy reading and search-discovery candidate

Static addition to the existing externally hosted grmove.com website. No deployment is performed by these tools.

Six guides and six articles live in content/guides.json and content/articles.json. Run python tools/build.py and python tools/check.py after changing public copy. The 15 built HTML pages and four support files are in dist/. Publish only dist contents through the existing website process, after copy review and reconciliation with newer homepage work.

Use the existing handoff publishing instructions for release, IndexNow and measurement. The 48 proposed test questions in operations/query-set.json include the unchanged 24 GR-Q2 guide questions and 24 GR-A2 series questions. The previous 36-query set is preserved in query-set.articles-v1.json. Query-set hashes prevent treating changed experiments as unchanged results. No baseline captures exist.

The preview is a noindex reading artifact, excluded from dist. Generate the handoff with python tools/package_handoff.py --output /absolute/path/to/existing-handoff-output-directory. The packaging command expects the existing publishing-instructions Markdown in that directory, preserves its installation guidance and updates scope. It does not publish or upload.

Review reader-intent-map.md for the qualitative evidence and archive-editorial-provenance.json for selected source pointers. These are internal editorial records. Articles are newly adapted drafts, not verbatim archived writing. No raw archive, private source documents, measured keyword volume, invented attribution or fabricated customer proof is included.
