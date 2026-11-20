# DOOM 3 BFG Edition 繁體中文化

非官方的《毀滅戰士 3：BFG 版》（DOOM 3 BFG Edition，Steam app 208200）繁體中文化。
本 repo 只有工具與譯文，**不含任何遊戲原始資源**，需自備正版遊戲。

## 進度

全部 8,514 條遊戲內字串已翻成繁體中文（含主選單、設定、PDA 郵件、語音日誌標題、任務目標、機台與門牌文字、邪惡復甦與失落任務）。術語表見 `docs/glossary.md`。譯文初稿由 AI 產生，歡迎回報錯譯。

## 原理

- 引擎會載入 `base/strings/` 底下所有 `english*.lang`，依檔名排序、後載的覆蓋先載的。
  本修正檔放一個 `english_zcht.lang`，排在 `english.lang` 之後，蓋掉英文字串。
- 語言檔裡的 `"#font_*"` 會把遊戲所有字型導向指定字型（官方日文版就是這樣掛日文字型的），
  這裡指向用思源黑體（Noto Sans TC，OFL 授權）產生的 `newfonts/chinese`。
- 字型只收譯文實際用到的字，所以字型在每次建置時重新產生。

## 建置與安裝

需要 Python 3.10+ 與 Pillow（`pip install pillow`），以及系統內的 Noto Sans TC（Windows 11 內建 `NotoSansTC-VF.ttf`，或用 `--font` 指定）。

```powershell
python tools/build.py --install "F:\SteamLibrary\steamapps\common\DOOM 3 BFG Edition"
```

移除：

```powershell
python tools/build.py --uninstall "F:\SteamLibrary\steamapps\common\DOOM 3 BFG Edition"
```

## 工具

| 檔案 | 用途 |
|---|---|
| `tools/d3res.py` | 列出／解出 `.resources` 容器 |
| `tools/make_font.py` | 產生 idFont（`48.dat` + `48.tga`） |
| `tools/build.py` | 合併譯文、產生字型與語言檔、安裝／移除 |
| `tools/check.py` | 檢查漏翻、變數與換行、簡體字 |

## 授權

工具程式碼：MIT。字型：Noto Sans TC，SIL Open Font License 1.1。
DOOM 為 id Software / ZeniMax 的商標，本專案與其無關。
