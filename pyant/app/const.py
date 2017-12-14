import os

if os.environ.get('SSH_GIT'):
    SSH_GIT = os.environ['SSH_GIT']
else:
    SSH_GIT = 'ssh://u3build@10.41.103.20:29418'

# ARTIFACT

if os.environ.get('ARTIFACT_HTTP'):
    ARTIFACT_HTTP = os.environ['ARTIFACT_HTTP']
else:
    ARTIFACT_HTTP = 'https://artsz.zte.com.cn/artifactory'

if os.environ.get('ARTIFACT_APIKEY'):
    ARTIFACT_APIKEY = os.environ['ARTIFACT_APIKEY']
else:
    ARTIFACT_APIKEY = 'AKCp5Z2hQNQxCGeuwsBh425oRswLznyxPG3y4cBxmYi5FYfvvquviLVwH8rNUnEKtkdEsonjW'

# METRIC

if os.environ.get('METRIC_HTTP'):
    METRIC_HTTP = os.environ['METRIC_HTTP']
else:
    METRIC_HTTP = 'http://10.41.213.28/WebService/ZTE.Wireline.WebService/BuildAPI.ashx'

if os.environ.get('METRIC_ID_BN_IPTN'):
    METRIC_ID_BN_IPTN = os.environ['METRIC_ID_BN_IPTN']
else:
    METRIC_ID_BN_IPTN = '310001141330'

if os.environ.get('METRIC_ID_BN_IPTN_NJ'):
    METRIC_ID_BN_IPTN_NJ = os.environ['METRIC_ID_BN_IPTN_NJ']
else:
    METRIC_ID_BN_IPTN_NJ = '310001141084'

if os.environ.get('METRIC_ID_BN_E2E'):
    METRIC_ID_BN_E2E = os.environ['METRIC_ID_BN_E2E']
else:
    METRIC_ID_BN_E2E = '310001142576'

if os.environ.get('METRIC_ID_BN_NBI'):
    METRIC_ID_BN_NBI = os.environ['METRIC_ID_BN_NBI']
else:
    METRIC_ID_BN_NBI = '310001142710'

if os.environ.get('METRIC_ID_BN_OTN'):
    METRIC_ID_BN_OTN = os.environ['METRIC_ID_BN_OTN']
else:
    METRIC_ID_BN_OTN = '310001141294'

if os.environ.get('METRIC_ID_STN'):
    METRIC_ID_STN = os.environ['METRIC_ID_STN']
else:
    METRIC_ID_STN = '310001141090'

if os.environ.get('METRIC_ID_UMEBN'):
    METRIC_ID_UMEBN = os.environ['METRIC_ID_UMEBN']
else:
    METRIC_ID_UMEBN = '310001127497'

if os.environ.get('METRIC_ID_SDNO'):
    METRIC_ID_SDNO = os.environ['METRIC_ID_SDNO']
else:
    METRIC_ID_SDNO = '310001127575'

# JENKINS

if os.environ.get('JENKINS_HTTP'):
    JENKINS_HTTP = os.environ['JENKINS_HTTP']
else:
    JENKINS_HTTP = 'http://10.8.9.80:8080'

if os.environ.get('JENKINS_USERNAME'):
    JENKINS_USERNAME = os.environ['JENKINS_USERNAME']
else:
    JENKINS_USERNAME = 'admin'

if os.environ.get('JENKINS_PASSWORD'):
    JENKINS_PASSWORD = os.environ['JENKINS_PASSWORD']
else:
    JENKINS_PASSWORD = 'admin-1234'

if os.environ.get('JENKINS_CLI'):
    JENKINS_CLI = os.environ['JENKINS_CLI']
else:
    JENKINS_CLI = '/build/jenkins/jenkins-cli.jar'
