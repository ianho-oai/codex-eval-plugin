# Normalize URL slugs

Fix `slug.py:slugify(text)` without changing its public signature.

The output must contain lowercase ASCII letters/digits separated by a single hyphen. Normalize Unicode using NFKD and discard non-ASCII code points; accented Latin characters should retain their ASCII base. Treat each run of non-alphanumeric characters (including underscores) as a separator, and trim leading/trailing separators. Empty or punctuation-only input returns an empty string. Raise TypeError for non-string inputs. Do not add dependencies.
