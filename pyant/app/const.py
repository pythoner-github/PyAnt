import os

if os.environ.get('SSH_GIT'):
    SSH_GIT = os.environ['SSH_GIT']
else:
    SSH_GIT = 'ssh://u3build@10.41.103.20:29418'

if os.environ.get('ARTIFACT_HTTP'):
    ARTIFACT_HTTP = os.environ['ARTIFACT_HTTP']
else:
    ARTIFACT_HTTP = 'https://artsz.zte.com.cn/artifactory'

if os.environ.get('ARTIFACT_USERNAME'):
    ARTIFACT_USERNAME = os.environ['ARTIFACT_USERNAME']
else:
    ARTIFACT_USERNAME = 'umebn-reader'

if os.environ.get('ARTIFACT_PASSWORD'):
    ARTIFACT_PASSWORD = os.environ['ARTIFACT_PASSWORD']
else:
    ARTIFACT_PASSWORD = 'umebn-reader_123456'
