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
                restrictedContributionsCount
                totalCommitContributions
            }
        }
    }
    """
    variables = {'start_date': start_date, 'end_date': end_date, 'user_name': USER_NAME}
    request = simple_request('graph_commits', query, variables)
    return request.json()['data']['user']['contributionsCollection']['totalCommitContributions']

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
    total_commits = graph_commits(created_at.strftime('%Y-%m-%dT%H:%M:%SZ'), datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'))
    
    repo_count, star_count = graph_repos_stars()
    contrib_count = user_data['repositoriesContributedTo']['totalCount']
    follower_count = follower_getter()
    
    loc_data = (1261, 198, 1063) 
    
    svg_overwrite('dark_mode.svg', age_str, total_commits, star_count, repo_count, contrib_count, follower_count, loc_data)
    svg_overwrite('light_mode.svg', age_str, total_commits, star_count, repo_count, contrib_count, follower_count, loc_data)
