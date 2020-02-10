// URLs
export const PATH_BASE = `${process.env.REACT_APP_API_BASE}`;

export const PATH_AUTH = `${PATH_BASE}/rest-auth`;
export const PATH_USER = `${PATH_AUTH}/user/`;
export const PATH_LOGIN = `${PATH_AUTH}/login/`;
export const PATH_REGISTER = `${PATH_AUTH}/registration/`;
export const PATH_GOOGLE = `${PATH_AUTH}/google/`;
export const PATH_LOGOUT = `${PATH_AUTH}/logout/`;
export const PATH_VERIFY_EMAIL = `${PATH_AUTH}/registration/verify-email/`;
export const PATH_REFRESH_TOKEN = `${PATH_AUTH}/refresh/`;

export const PATH_DASHBOARD = `${PATH_BASE}/dashboard/`;
export const PATH_COMPLETE_SPRINT = `${PATH_DASHBOARD}complete_sprint/`;
export const USE_CACHE = 'cache=true';

export const PATH_SUSTAINABILITY_DASHBOARD = `${PATH_BASE}/sustainability/dashboard/`;
export const PARAM_FROM = 'from=';
export const PARAM_TO = 'to=';

export const PATH_JIRA_BASE = `${process.env.REACT_APP_JIRA_URL}`;
export const PATH_JIRA_ISSUE = `${PATH_JIRA_BASE}/browse/`;

// Sprints
export const UNASSIGNED_NAME = "Unassigned";
export const OTHER_CELL_NAME = "Other Cell";
export const SPECIAL_USER_NAMES = [UNASSIGNED_NAME, OTHER_CELL_NAME];

// Sustainability
export const COMPANY_NAME = `${process.env.REACT_APP_COMPANY_NAME}`;
export const MAX_NON_BILLABLE_TO_BILLABLE_RATIO = parseFloat(process.env.REACT_APP_MAX_NON_BILLABLE_TO_BILLABLE_RATIO);
export const MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO = parseFloat(process.env.REACT_APP_MAX_NON_BILLABLE_TO_BILLABLE_CELL_RATIO);
export const ACCOUNT_STRIP_NAMES = JSON.parse(process.env.REACT_APP_ACCOUNT_STRIP_NAMES);

// Docs
export const DOCS = process.env.REACT_APP_DOCS;
export const SPRINTS_DOCS =`${DOCS}#sprints`;
export const SUSTAINABILITY_DASHBOARD_DOCS =`${DOCS}#sustainability-dashboard`;
export const BUDGET_DASHBOARD_DOCS =`${DOCS}#budget-dashboard`;
