# Developer notes

## vrnetlab module and vscode pylance

since vrnetlab module is in the `common` dir the pylance extension in vscode will not be able to find the module reference in `launch.py` files. To fix this, add the following to the `settings.json` file in vscode:

```json
{
    "python.analysis.extraPaths": ["common"]
}
```
