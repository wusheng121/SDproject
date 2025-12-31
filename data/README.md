## 电影数据放这里（推荐 MovieLens）

课程项目想要“真实电影数据”，推荐用 **MovieLens**（公开数据集，适合课程/实验）。

你需要准备的文件（至少一个）：
- `movies.csv`（必须）：包含 `movieId,title,genres`
- `ratings.csv`（可选）：包含用户评分（本项目不建议直接导入到你自己的 Rating 表，避免混淆“真实用户评分”和“数据集评分”）

下载方式（自行浏览器下载后解压）：
- GroupLens MovieLens：`https://grouplens.org/datasets/movielens/`

把解压出来的 `movies.csv` 放到本目录（`data/movies.csv`），然后运行导入脚本：

```bash
cd backend
python -m seed.import_movielens --movies ..\data\movies.csv
```

导入时会自动把 MovieLens 的标题格式（如 `Great Gatsby, The (1974)`）还原为 `The Great Gatsby (1974)` 并写入数据库；同时默认会导出一个对照表方便你抽查：
- 输出：`data/movies_normalized_preview.csv`

如果你还想让电影有 **简介/海报/演员**（MovieLens 没有这些字段），建议用 TMDB 补全：
- 你需要自己申请 TMDB API Key：`https://www.themoviedb.org/settings/api`
- 然后执行：

```bash
cd backend
$env:TMDB_API_KEY="你的key"
python -m seed.enrich_tmdb --limit 200
```

导入完成后，启动后端即可通过 `/api/movies` 看到真实列表数据。


