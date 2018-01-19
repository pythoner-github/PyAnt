import os
import os.path

if os.environ.get('SSH_GIT'):
    SSH_GIT = os.environ['SSH_GIT']
else:
    # ssh://u3build@gerrit.zte.com.cn:29418
    SSH_GIT = 'ssh://u3build@10.41.103.20:29418'

# ARTIFACT

if os.environ.get('ARTIFACT_HTTP'):
    ARTIFACT_HTTP = os.environ['ARTIFACT_HTTP']
else:
    # https://artsz.zte.com.cn/artifactory
    ARTIFACT_HTTP = 'https://10.31.126.100/artifactory'

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

if os.environ.get('JENKINS_URL'):
    JENKINS_URL = os.environ['JENKINS_URL']
else:
    JENKINS_URL = 'http://10.8.9.85:8080'

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
    if os.environ.get('JENKINS_HOME'):
        JENKINS_CLI = os.path.join( os.environ['JENKINS_HOME'], 'jenkins-cli.jar')
    else:
        JENKINS_CLI = '/build/jenkins/jenkins-cli.jar'

# PATCH

PATCH_XML_HOME = '/home/build/auto/xml'
PATCH_TEMPLATE_HOME = os.path.abspath(os.path.join(PATCH_XML_HOME, '..', 'template'))

PATCH_NODE_INFO = {
    'stn/none'      : ['10.5.72.12',  '/build'],
    'bn/linux'      : ['10.5.72.101', '/build/build'],
    'bn/solaris'    : ['10.5.72.102', '/build/build'],
    'bn/windows'    : ['10.8.11.106', 'd:/build'],
    'bn/windows_x86': ['10.8.11.106', 'e:/build']
}