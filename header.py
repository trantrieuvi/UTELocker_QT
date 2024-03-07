#Define API header
api_headers = {
            "X-License-Hash": "fa01f9cb4ead7d12bf494c408d897adcfbf420c9b36ede04445e7b1c8e64c5a81d86eefeb49303c55d4cc3e8c42f78e423a233e8fdf60eb5cce2855f05b59996",
            "X-License-Id": "1",
            "X-License-Time": "2023/11/15 10:00",
        }

#Unlock API
unlock_url = "https://utelocker.dataviz.io.vn/api_qt/password"
sync_url = "https://utelocker.dataviz.io.vn/api_qt/sync"
log_active_url = "https://utelocker.dataviz.io.vn/api_qt/log-active"
pusher_url = "https://utelocker.dataviz.io.vn/api_qt/set-up/config"
reset_pass_url = "https://utelocker.dataviz.io.vn/api_qt/reset-pass"

API_TIMEOUT = 2
API_ERROR = 0
API_OK = 1
PASSWORD_CORRECT = 1
PASSWORD_INCORRECT = 0
UNLOCK_OK = 1
UNLOCK_ERROR = 0
CHECK_OK = 1
CHECK_ERROR = 0
USER_MODE = 1
ADMIN_MODE = 2

