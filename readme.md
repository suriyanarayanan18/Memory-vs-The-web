# Memory vs the Web

*What an AI recommends before and after RAG (retrieval-augmented generation).*

What an AI recommends from memory is not what it recommends from the web. This is a small experiment on that gap, using running shoes as the test category.

Thirty real buyer questions were each asked two ways: once with the model answering from training memory (no internet), and once with live web search on. Then I measured which brands showed up and which sources got cited.

**Live site:** https://memory-vs-the-web.vercel.app/

## What I found

- **Brands shift hard between modes.** New Balance fell 43 points in share of voice when search was on, and Brooks fell 23. Adidas rose 30. The model's memory over-recommends some brands relative to what current reviews actually say.
- **Search widens the brand set.** Mizuno, Kiprun, Topo, and others appeared only with web search on. They are invisible to the model's memory but real in live results.
- **Visibility runs through a few sites.** Of 55 distinct cited domains, one (RunRepeat) was cited in 22 of 30 searched answers. The top three sources carried most citations. Winning AI visibility means earning a place on a short list, not the whole web.

## How it works

A four step pipeline:

1. **`queries.csv`** holds the 30 questions across five intent types (category, problem, use case, budget, comparison).
2. **`collect.py`** and **`collect_retrieval.py`** ask each question, the first from memory and the second with web search on, saving raw answers.
3. **`extract.py`** uses a model to pull brand mentions from each answer and reduces cited URLs to clean domains, writing **`structured.jsonl`**.
4. **`analyze.py`** computes share of voice and the memory vs web gap. **`build_site.py`** bakes the results into **`index.html`**, the standalone site.

## Run it

```
pip install anthropic pandas
set your ANTHROPIC_API_KEY as an environment variable
python collect.py
python collect_retrieval.py
python extract.py
python analyze.py
python build_site.py
```

Open `index.html` in any browser. No server needed.

## Limitations

Single run per question, so brands at very low share are noise rather than trends. One engine, so results do not transfer to other AI search tools. A snapshot in time, since web results change.

## Stack

Python, Anthropic API (with the web search tool), pandas. The site is hand built HTML, CSS, and JavaScript with no framework.
