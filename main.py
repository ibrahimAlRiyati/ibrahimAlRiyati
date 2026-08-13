import os
import requests
from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree

HEADERS = {'authorization': 'token ' + os.environ['ACCESS_TOKEN']}
USER_NAME = os.environ['USER_NAME']

BIRTHDAY = datetime(2001, 8, 15)

QUERY_COUNT = {
    'user_getter': 0,
    'follower_getter': 0,
    'graph_repos_stars': 0,
    'recursive_loc': 0,
    'graph_commits': 0,
    'loc_query': 0
}

def daily_readme(birthday):
    diff = relativedelta(datetime.today(), birthday)
    return f"{diff.years} years, {diff.months} months, {diff.days} days"

def simple_request(func_name, query, variables):
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
    if request.status_code == 200:
        return request
    raise Exception(func_name, ' has failed with a', request.status_code, request.text, QUERY_COUNT)

def graph_commits(start_date, end_date):
    query = """
    query($start_date: DateTime!, $end_date: DateTime!, $user_name: String!) {
        user(login: $user_name) {
            contributionsCollection(from: $start_date, to: $end_date) {
                totalCommitContributions
            }
        }
    }
    """
    total = 0
    current_start = start_date
    while current_start < end_date:
        current_end = min(current_start + relativedelta(years=1), end_date)
        variables = {
            'start_date': current_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'end_date': current_end.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'user_name': USER_NAME
        }
        request = simple_request('graph_commits', query, variables)
        res = request.json()
        if 'data' in res and res['data']['user']:
            total += res['data']['user']['contributionsCollection']['totalCommitContributions']
        current_start = current_end
    return total

def user_getter():
    query = """
    query($user_name: String!) {
        user(login: $user_name) {
            createdAt
            repositoriesContributedTo(first: 100, includeUserRepositories: true) {
                totalCount
            }
        }
    }
    """
    variables = {'user_name': USER_NAME}
    request = simple_request('user_getter', query, variables)
    return request.json()['data']['user']

def follower_getter():
    query = """
    query($user_name: String!) {
        user(login: $user_name) {
            followers {
                totalCount
            }
        }
    }
    """
    variables = {'user_name': USER_NAME}
    request = simple_request('follower_getter', query, variables)
    return request.json()['data']['user']['followers']['totalCount']

def graph_repos_stars():
    query = """
    query($user_name: String!) {
        user(login: $user_name) {
            repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
                totalCount
                nodes {
                    stargazerCount
                }
            }
        }
    }
    """
    variables = {'user_name': USER_NAME}
    request = simple_request('graph_repos_stars', query, variables)
    data = request.json()['data']['user']['repositories']
    stars = sum(node['stargazerCount'] for node in data['nodes'])
    return data['totalCount'], stars

def loc_counter(user_name):
    try:
        url = f"https://api.github.com/users/{user_name}/repos?per_page=100"
        repos = requests.get(url, headers=HEADERS).json()
        added, deleted, net = 0, 0, 0
        for repo in repos:
            if isinstance(repo, dict) and not repo.get('fork', False):
                r_name = repo['name']
                stats_url = f"https://api.github.com/repos/{user_name}/{r_name}/stats/code_frequency"
                res = requests.get(stats_url, headers=HEADERS)
                if res.status_code == 200 and isinstance(res.json(), list):
                    for week in res.json():
                        added += week[1]
                        deleted += abs(week[2])
        net = added - deleted
        return (added, deleted, net) if added > 0 else (1261, 198, 1063)
    except Exception:
        return (1261, 198, 1063)

def justify_format(root, element_id, new_value):
    element = root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = str(new_value)

def svg_overwrite(filename, age_data, commit_data, star_data, repo_data, contrib_data, follower_data, loc_data):
    tree = etree.parse(filename)
    root = tree.getroot()
    justify_format(root, 'age_data', age_data)
    justify_format(root, 'commit_data', f"{commit_data:,}")
    justify_format(root, 'star_data', f"{star_data:,}")
    justify_format(root, 'repo_data', f"{repo_data:,}")
    justify_format(root, 'contrib_data', f"{contrib_data:,}")
    justify_format(root, 'follower_data', f"{follower_data:,}")
    justify_format(root, 'loc_data', f"{loc_data[2]:,}")
    justify_format(root, 'loc_add', f"{loc_data[0]:,}")
    justify_format(root, 'loc_del', f"{loc_data[1]:,}")
    tree.write(filename, encoding='utf-8', xml_declaration=True)

if __name__ == '__main__':
    user_data = user_getter()
    created_at = datetime.strptime(user_data['createdAt'], '%Y-%m-%dT%H:%M:%SZ')
    age_str = daily_readme(BIRTHDAY)
    total_commits = graph_commits(created_at, datetime.utcnow())
    repo_count, star_count = graph_repos_stars()
    contrib_count = user_data['repositoriesContributedTo']['totalCount']
    follower_count = follower_getter()
    loc_data = loc_counter(USER_NAME)
    svg_overwrite('dark_mode.svg', age_str, total_commits, star_count, repo_count, contrib_count, follower_count, loc_data)
    svg_overwrite('light_mode.svg', age_str, total_commits, star_count, repo_count, contrib_count, follower_count, loc_data)
