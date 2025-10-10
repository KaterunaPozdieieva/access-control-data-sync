# web/coolsite/api_config.py

API_URL = 'http://sr00041895.medi.local:8080/api/v1/'

TOKEN_URL = f'{API_URL}authorization/tokens'
USER_URL = f'{API_URL}users/'
DEPARTMENT_URL = f'{API_URL}users/{{userId}}/departments'
DOOR_PERMISSION_URL = f'{API_URL}users/{{userId}}/doorpermissionset'
DOOR_URL = f'{API_URL}doors/'
ACCESS_LEVELS_URL = f'{API_URL}accesslevels/'
DB_URL = f'{API_URL}customquery/querydb'
DOORS_URL = f'{API_URL}doors/'
ACCESS_LEVELS_SHORT_URL = f'{API_URL}accesslevels'
