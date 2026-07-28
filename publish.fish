set newversion (sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml)
git commit -am "new v$newversion"
git tag -a v$newversion -m "v$newversion"
git push --tags
uv build
uv publish --username __token__ --password (rbw get "pypi" "00sapo" -f "token")
gh release create "v$newversion" --verify-tag --generate-notes --title "v$newversion"
