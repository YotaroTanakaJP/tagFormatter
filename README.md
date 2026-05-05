# tagFormatter

CSVファイルからFLACのVorbis Commentを更新するCLIツールです。

## セットアップ

必ずプロジェクト直下の `.venv` を使ってください。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e .[dev]
```

## CSVフォーマット

正式なテンプレートは [examples/tags_template.csv](examples/tags_template.csv) です。

対象指定列:

- `file_path`: 対象の `.flac` ファイルへの相対パスまたは絶対パス
- `track`: `--album-dir` 使用時のトラック番号

補助列:

- `disc`: `--album-dir` 使用時に対象ディスクを絞り込むための番号

任意列:

- `album_title`
- `album_artist`
- `artist_name`
- `genre`
- `date`
- `comment`
- `composer`
- `performer`
- `track_title`
- `conductor`

空セルは「そのタグを変更しない」として扱います。
既存タグを削除したい場合は、対象セルに `__CLEAR__` を指定してください。
複数値タグは `A; B; C` のようにセミコロン区切りで指定できます。

互換用エイリアスとして、以下の列名も受け付けます。

- `Album Artist` -> `album_artist`
- `Artist` -> `artist_name`
- `Genre` -> `genre`
- `Year` -> `date`
- `Comment` -> `comment`
- `Composer` -> `composer`
- `Performer` -> `performer`
- `Title` -> `track_title`
- `Conductor` -> `conductor`

`Disc` と `Track` は対象ファイルの選択にのみ使い、タグとしては書き込みません。

現在開いているような `Disc,Track,Artist,...` 形式のCSVも、そのまま `--album-dir` と組み合わせて使えます。

## アルバム単位での実行

アルバムフォルダを指定すると、その配下の `.flac` を再帰的に探索して処理します。

```bash
.venv/bin/tagformatter --csv /Users/yotarotanaka/Downloads/tag.csv --album-dir "/Users/yotarotanaka/Downloads/FLAC_RIP/[unnamed]/Eugene Ormandy conducts 20th Century Classics (CD7)/Eugene Ormandy" --dry-run
```

このモードでは次の順でファイルを対応づけます。

1. FLAC に埋め込まれている `DISCNUMBER` / `TRACKNUMBER`（または `DISC` / `TRACK`）タグで `Disc` / `Track` 列に対応づける
2. それができず、ファイル名が `01 ...flac` のようにトラック番号で始まっていれば、その番号で `Track` 列に対応づける
3. それもできず、CSVの `Track` が `1..N` の連番で、見つかった `.flac` 数と一致する場合は並び順で対応づける

`1-01 ...flac` / `2-01 ...flac` のような平置き構成でも、各 FLAC に `DISCNUMBER` と `TRACKNUMBER` が入っていれば `--album-dir` で直接処理できます。

`Disc` が複数含まれるCSVでも、FLAC 側に `DISCNUMBER` / `TRACKNUMBER` が入っていればそのまま一括処理できます。単一ディスクだけ処理したい場合は、引き続き `--disc 7` のように指定するか、パス中の `CD7` から自動推定できます。

## 実行例

```bash
.venv/bin/tagformatter --csv examples/tags_template.csv --base-dir /path/to/flac --dry-run
.venv/bin/tagformatter --csv tags.csv --base-dir /path/to/flac
.venv/bin/tagformatter --csv /Users/yotarotanaka/Downloads/tag.csv --album-dir "/path/to/album/CD7/Artist" --dry-run
```

## オプション

- `--csv`: 入力CSVファイル
- `--base-dir`: `file_path` を解決する基準ディレクトリ
- `--album-dir`: 配下の `.flac` をアルバム単位で処理するディレクトリ
- `--disc`: `Disc` 列から処理対象を選ぶ番号
- `--dry-run`: 実際には書き込まず、変更予定だけ表示

## 拡張方法

タグを増やしたい場合は、[src/tagformatter/tag_mapping.py](src/tagformatter/tag_mapping.py) の `DEFAULT_TAG_MAPPINGS` にCSV列名とFLACタグ名を追加してください。

`Disc` や `Track` の列名エイリアスを増やしたい場合は、[src/tagformatter/csv_loader.py](src/tagformatter/csv_loader.py) の `DISC_COLUMNS` と `TRACK_COLUMNS` を更新してください。
