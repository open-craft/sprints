// URLs
export const PATH_BASE = `${process.env.REACT_APP_API_BASE}`;

export const PATH_AUTH = `${PATH_BASE}/rest-auth`;
export const PATH_USER = `${PATH_AUTH}/user/`;
export const PATH_LOGIN = `${PATH_AUTH}/login/`;
export const PATH_REGISTER = `${PATH_AUTH}/registration/`;
export const PATH_GOOGLE = `${PATH_AUTH}/google/`;
export const PATH_LOGOUT = `${PATH_AUTH}/logout/`;
export const PATH_VERIFY_EMAIL = `${PATH_AUTH}/registration/verify-email/`;

export const PATH_SPRINT_DASHBOARD = `${PATH_BASE}/dashboard`;
export const PATH_CELLS = `${PATH_SPRINT_DASHBOARD}/cells/`;
export const PATH_DASHBOARD = `${PATH_SPRINT_DASHBOARD}/dashboard/`;
export const PARAM_BOARD_ID = 'board_id=';
export const PATH_COMPLETE_SPRINT = `${PATH_SPRINT_DASHBOARD}/complete_sprint/`;
export const PATH_CREATE_NEXT_SPRINT = `${PATH_SPRINT_DASHBOARD}/create_next_sprint/`;

export const PATH_SUSTAINABILITY_DASHBOARD = `${PATH_BASE}/sustainability/dashboard/`;
export const PARAM_FROM = 'from=';
export const PARAM_TO = 'to=';
export const PARAM_YEAR = 'year=';

export const PATH_JIRA_BASE = `${process.env.REACT_APP_JIRA_URL}`;
export const PATH_JIRA_ISSUE = `${PATH_JIRA_BASE}/browse/`;

// Sustainability
export const MAX_NON_BILLABLE_TO_BILLABLE_RATIO = parseFloat(process.env.REACT_APP_MAX_NON_BILLABLE_TO_BILLABLE_RATIO);
