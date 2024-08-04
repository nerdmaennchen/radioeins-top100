import werkzeug
werkzeug.cached_property = werkzeug.utils.cached_property

from robobrowser import RoboBrowser
import bs4

import pickle
from pathlib import Path
import urllib.parse
import sys
import re
import os
from difflib import get_close_matches

def extractText(elem):
    if type(elem) == bs4.element.ResultSet:
        return ", ".join([u''.join(e.findAll(text=True)).strip() for e in elem])
    return u''.join(elem.findAll(string=True)).strip()


def correctName(performer, title):
    return performer, title
    qry = urllib.parse.quote(f'{performer} {title}')
    correct_name_browser = RoboBrowser(history=True, parser="html.parser", user_agent="")
    correct_name_browser.open('https://www.allmusic.com/search/songs/' + qry)
    try:
        top_result = correct_name_browser.select(".results .song")[0]
        p, t = extractText(top_result.select(".performers a")), extractText(top_result.select(".title")[0])[1:-1]
        if p and t:
            performer, title = p, t
    except Exception as e:
        # print(e)
        pass
    return performer, title

def extractVotes(browser):
    tr = browser.select("article.layoutarticlemodule tr")
    weighting = { "1": 12, "2": 10, "3": 8, "4": 7, "5": 6, "6": 5, "7": 4, "8": 3, "9": 2, "10": 1, }
    results = {}
    for row in tr:
        try:
            rank, artist, title = row.select("td")[:3]
            rank, artist, title = extractText(rank), extractText(artist), extractText(title)
            artist, title = correctName(artist, title);
            name = f"{artist} - {title}"

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

    votes = browser.select('section.layoutpagerbox a.beitrag')
    followed_links = set()

    total_scores = {}

    for v in votes:
        tgt = os.path.basename((v['href']))
        if tgt in followed_links:
            continue

        print(tgt)
        browser.follow_link(v)
        followed_links.add(tgt)
        
        try:
            scores = extractVotes(browser)
            print(scores)
            total_scores[tgt] = scores
        except Exception as e:
            print(e)
        browser.back()
    return total_scores

def process_votes(votes):
    total_scores = {}
    for _, scores in votes.items():
        for title, score in scores.items():
            if title not in total_scores:
                total_scores[title] = (score, 1)
            else:
                score_, num = total_scores[title]
                total_scores[title] = (score_+score, num+1)
    return total_scores

def deduplicate_scores(scores):
    deduplicated_scores = {}
    for title, (score, num) in scores.items():
        matches = get_close_matches(title, deduplicated_scores.keys(), n=1, cutoff=.9)
        if len(matches):
            print(f"merging '{matches[0]}' into '{title}'")
            title = matches[0]
            s, n = deduplicated_scores[title]
            score += s
            num += n
        deduplicated_scores[title] = (score, num)
    return deduplicated_scores


def cache_categories(url, path, cache_file):
    if not cache_file.is_file():
        browser = RoboBrowser(history=True, parser="html.parser")
        browser.open('%s%s' % (url, path))
        links = browser.select('a.uebersicht')
        found_links = set();
        for l in links:
            ll = re.findall(f"^{path}(.*)/index.html$", l['href']) 
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
    path = '/musik/top_100/2024/'

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

    cache_file = Path(f"cache/{target}_cached_results")
    results_file = Path(f"{target}_results")

    votes = None
    try:
        if cache_file.is_file():
            with cache_file.open('rb') as f:
                votes = pickle.load(f)
    except Exception as e:
        print(e)
    if votes == None or len(votes) == 0:
        votes = fetch(f'{url}{path}{target}/')
        if not os.path.exists("cache"):
            os.makedirs("cache")
        with cache_file.open('wb') as f:
            pickle.dump(votes, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    ## process votes
    total_scores = process_votes(votes)
    total_scores = deduplicate_scores(total_scores)


    scores = [(val, text) for text, val in total_scores.items()]
    scores.sort(key=lambda element: (-element[0][0], -element[0][1], element[1]))

    with results_file.open("w") as f:
        f.write("\n".join(["%d %d (%d) %s" % (rank+1, score, num, title) for rank, ((score, num), title) in enumerate(scores)]))
