const initialState = {
    isAuthenticated: null,
    isLoading: true,
    user: null,
    errors: {},
};


export default function auth(state=initialState, action) {

    switch (action.type) {

        case 'USER_LOADING':
            return {...state, isLoading: true};

        case 'USER_LOADED':
            return {...state, isAuthenticated: true, isLoading: false, user: action.user};

        case 'LOGIN_SUCCESSFUL':
        case 'REGISTRATION_SUCCESSFUL':
            localStorage.setItem("access_token", action.data.access_token);
            localStorage.setItem("refresh_token", action.data.refresh_token);
            return {...state, ...action.data, isAuthenticated: true, isLoading: false, errors: null};

        case 'EMAIL_VERIFICATION_SUCCESSFUL':
            return {...state, emailConfirmed: true};

        case 'AUTHENTICATION_ERROR':
        case 'LOGIN_FAILED':
        case 'REGISTRATION_FAILED':
        case 'LOGOUT_SUCCESSFUL':
        case 'EMAIL_VERIFICATION_FAILED':
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");

            // Handle non-standard error Object from simpleJWT.
            if (action.data && action.data.messages) {
                action.data = action.data.messages.map(entry => entry.message);
            }

            return {...state, errors: action.data, user: null,
                isAuthenticated: false, isLoading: false};

        default:
            return state;
    }
}
