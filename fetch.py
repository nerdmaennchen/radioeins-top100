from robobrowser import RoboBrowser
import pickle
from pathlib import Path
import sys

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

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("usage: python fetch [list]")
        exit(-1)
    target = sys.argv[1]

    cache_file = Path(target + "_cached_results")
    results_file = Path(target + "_results")

    if not cache_file.is_file():
        total_scores = fetch('https://www.radioeins.de/musik/die-100-besten-2019/' + target + '/')
        with cache_file.open('wb') as f:
            pickle.dump(total_scores, f, protocol=pickle.HIGHEST_PROTOCOL)


    with cache_file.open('rb') as f:
        total_scores = pickle.load(f)

    scores = [(val, text) for text, val in total_scores.items()]
    scores.sort(reverse=True)

    with results_file.open("w") as f:
        f.write("\n".join([str(rank+1) + " " + str(score) + " (" + str(num) + ") " + title for rank, ((score, num), title) in enumerate(scores)]))
    

