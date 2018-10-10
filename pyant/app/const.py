import collections
import os
import os.path
import sys

from pyant.builtin import __os__

if os.environ.get('SSH_GIT'):
    SSH_GIT = os.environ['SSH_GIT']
else:
    # ssh://u3build@gerrit.zte.com.cn:29418
    SSH_GIT = 'ssh://u3build@10.41.103.20:29418'

# REPOS

BN_REPOS = collections.OrderedDict([
    ('interface', __os__.join(SSH_GIT, 'U31R22_INTERFACE')),
    ('platform' , __os__.join(SSH_GIT, 'U31R22_PLATFORM')),
    ('necommon' , __os__.join(SSH_GIT, 'U31R22_NECOMMON')),
    ('e2e'      , __os__.join(SSH_GIT, 'U31R22_E2E')),
    ('uca'      , __os__.join(SSH_GIT, 'U31R22_UCA')),
    ('xmlfile'  , __os__.join(SSH_GIT, 'U31R22_NBI_XMLFILE')),
    ('nbi'      , __os__.join(SSH_GIT, 'U31R22_NBI')),
    ('sdh'      , __os__.join(SSH_GIT, 'U31R22_SDH')),
    ('wdm'      , __os__.join(SSH_GIT, 'U31R22_WDM')),
    ('ptn'      , __os__.join(SSH_GIT, 'U31R22_PTN')),
    ('ptn2'     , __os__.join(SSH_GIT, 'U31R22_PTN2')),
    ('inventory', __os__.join(SSH_GIT, 'U31R22_Inventory'))
])

UMEBN_REPOS = __os__.join(SSH_GIT, 'umebn')

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
    METRIC_HTTP = 'http://10.46.205.130/WebService/ZTE.Wireline.WebService/BuildAPI.ashx'

if os.environ.get('METRIC_ID_BN_ITN'):
    METRIC_ID_BN_ITN = os.environ['METRIC_ID_BN_ITN']
else:
    METRIC_ID_BN_ITN = '310001152622'

if os.environ.get('METRIC_ID_BN_IPN'):
    METRIC_ID_BN_IPN = os.environ['METRIC_ID_BN_IPN']
else:
    METRIC_ID_BN_IPN = '310001151021'

if os.environ.get('METRIC_ID_BN_E2E'):
    METRIC_ID_BN_E2E = os.environ['METRIC_ID_BN_E2E']
else:
    METRIC_ID_BN_E2E = '310001152310'

if os.environ.get('METRIC_ID_BN_NBI'):
    METRIC_ID_BN_NBI = os.environ['METRIC_ID_BN_NBI']
else:
    METRIC_ID_BN_NBI = '310001152322'

if os.environ.get('METRIC_ID_BN_OTN'):
    METRIC_ID_BN_OTN = os.environ['METRIC_ID_BN_OTN']
else:
    METRIC_ID_BN_OTN = '310001151841'

if os.environ.get('METRIC_ID_STN'):
    METRIC_ID_STN = os.environ['METRIC_ID_STN']
else:
    METRIC_ID_STN = '310001152801'

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

# EMAIL
PYRO_MAIL = 'PYRO:daemon.mail@10.8.11.107:9000'

# PATCH

PATCH_XML_HOME = '/build/auto/xml'
PATCH_TEMPLATE_HOME = os.path.abspath(os.path.join(PATCH_XML_HOME, '..', 'template'))

PATCH_NODE_INFO = {
    'umebn/none'    : ['10.8.8.196',  '/build/build'],
    'bn/linux'      : ['10.5.72.101', '/build/build'],
    'bn/windows'    : ['10.8.11.106', 'd:/build/build'],
    'bn/windows_x86': ['10.8.11.106', 'e:/build/build']
}

# KLOCWORK

if os.environ.get('KLOCWORK_HTTP'):
    KLOCWORK_HTTP = os.environ['KLOCWORK_HTTP']
else:
    KLOCWORK_HTTP = 'http://10.8.10.15:8080'

if os.environ.get('KLOCWORK_PCONF_FILE'):
    KLOCWORK_PCONF_FILE = os.environ['KLOCWORK_PCONF_FILE']
else:
    KLOCWORK_PCONF_FILE = '/opt/analysis_profile.pconf'

if os.environ.get('KLOCWORK_LICENSE_HOST'):
    KLOCWORK_LICENSE_HOST = os.environ['KLOCWORK_LICENSE_HOST']
else:
    KLOCWORK_LICENSE_HOST = '10.42.171.61'

if os.environ.get('KLOCWORK_LICENSE_PORT'):
    KLOCWORK_LICENSE_PORT = os.environ['KLOCWORK_LICENSE_PORT']
else:
    KLOCWORK_LICENSE_PORT = '27000'

if os.environ.get('KLOCWORK_DATE'):
    KLOCWORK_DATE = os.environ['KLOCWORK_DATE']
else:
    KLOCWORK_DATE = '2018-09-01 00:00:00'

# UMEBN

OKI_FILE = 'devops/parent/ci_scripts/docker/scripts/patch.py'
