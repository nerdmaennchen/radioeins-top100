from robobrowser import RoboBrowser
import pickle
from pathlib import Path
import sys
import re
import os

def extractVotes(browser):
    tr = browser.select("div.articlesContList tr")
    weighting = {
        "1": 12,
        "2": 10,
        "3": 8,
        "4": 7,
        "5": 6,
        "6": 5,
        "7": 4,
        "8": 3,
        "9": 2,
        "10": 1,
    }
    results = {}
    for row in tr:
        def extractText(elem):
            return u''.join(elem.findAll(text=True)).strip()
        try:
            rank, artist, title = row.select("td")[:3]
            rank, artist, title = extractText(rank), extractText(artist), extractText(title)
            name = artist + " - " + title
            if rank in weighting:
                results[name] = weighting[rank]
        except Exception as e:
            print(e)
    if len(results) != 10:
        print(browser)
    return results

def fetch(url):
    browser = RoboBrowser(history=True, parser="html.parser")
    browser.open(url)

    votes = browser.select('.moderatorenSlider a.beitrag')
    followed_links = set()

    total_scores = {}

    for v in votes:
        if v["href"] in followed_links:
            continue
        else:
            followed_links.add(v["href"])
        print(v["href"])
        browser.follow_link(v)
        try:
            scores = extractVotes(browser)
            print(scores)
            for title, score in scores.items():
                if title not in total_scores:
                    total_scores[title] = (score, 1)
                else:
                    score_, num = total_scores[title]
                    total_scores[title] = (score_+score, num+1)
        except Exception as e:
            print(e)
        browser.back()
    return total_scores

def cache_categories(url, path, cache_file):
    if not cache_file.is_file():
        browser = RoboBrowser(history=True, parser="html.parser")
        browser.open('%s%s' % (url, path))
        links = browser.select('a.uebersicht')
        found_links = set();
        for l in links:
            ll = re.findall("^%s(.*)/index.html$" % path, l['href']) 
            if len(ll) == 1:
                found_links.add(ll[0])

        if not os.path.exists("cache"):
            os.makedirs("cache")
        with cache_file.open('wb') as f:
            pickle.dump(found_links, f, protocol=pickle.HIGHEST_PROTOCOL)

def load_categories(url, path):
    cache_file = Path("cache/categories")
    cache_categories(url, path, cache_file)

    if not cache_file.is_file():
        cache_categories(url, path, cache_file);

    with cache_file.open('rb') as f:
        found_links = pickle.load(f)
    return found_links


if __name__ == '__main__':
    url = 'https://www.radioeins.de'
    path = '/musik/die-100-besten-2019/'

    categories = load_categories(url, path)
    if len(sys.argv) != 2:
        print("usage: python fetch.py [--list | <category>]")
        exit(-1)

    target = sys.argv[1]
    if target == "--list":
        print("category:")
        for l in categories:
            print("  - %s" % l)
        exit(0)

    if target not in categories:
        print("error: invalid category")
        exit(0);

    cache_file = Path("cache/%s_cached_results" % target)
    results_file = Path("%s_results" % target)

    if not cache_file.is_file():
        total_scores = fetch('%s%s%s/' % (url, path, target))

        if not os.path.exists("cache"):
            os.makedirs("cache")
        with cache_file.open('wb') as f:
            pickle.dump(total_scores, f, protocol=pickle.HIGHEST_PROTOCOL)


    with cache_file.open('rb') as f:
        total_scores = pickle.load(f)

    scores = [(val, text) for text, val in total_scores.items()]
    scores.sort(reverse=True)

    with results_file.open("w") as f:
        f.write("\n".join(["%d %d (%d) %s" % (rank+1, score, num, title) for rank, ((score, num), title) in enumerate(scores)]))
