import {PATH_GOOGLE, PATH_LOGIN, PATH_LOGOUT, PATH_REGISTER, PATH_USER, PATH_VERIFY_EMAIL} from "../constants";

export const loadUser = () => {
    return (dispatch, getState) => {
        dispatch({type: "USER_LOADING"});

        const token = getState().auth.token;

        let headers = {
            "Content-Type": "application/json",
        };

        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }
        return fetch(PATH_USER, {headers,})
            .then(res => {
                if (res.status < 500) {
                    return res.json().then(data => {
                        return {status: res.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw res;
                }
            })
            .then(res => {
                if (res.status === 200) {
                    dispatch({type: 'USER_LOADED', user: res.data});
                    return res.data;
                } else if (res.status >= 400 && res.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: res.data});
                    throw res.data;
                }
            })
    }
};

export const login = (email, password) => {
    return (dispatch, getState) => {
        let headers = {"Content-Type": "application/json"};
        let body = JSON.stringify({email, password});

        return fetch(PATH_LOGIN, {headers, body, method: "POST"})
            .then(res => {
                if (res.status < 500) {
                    return res.json().then(data => {
                        return {status: res.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw res;
                }
            })
            .then(res => {
                if (res.status === 200) {
                    dispatch({type: 'LOGIN_SUCCESSFUL', data: res.data});
                    return res.data;
                } else if (res.status === 403 || res.status === 401) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: res.data});
                    throw res.data;
                } else {
                    dispatch({type: "LOGIN_FAILED", data: res.data});
                    throw res.data;
                }
            })
    }
};

export const social_login = (access_token) => {
    return (dispatch, getState) => {
        let headers = {"Content-Type": "application/json"};
        let body = JSON.stringify({access_token});

        return fetch(PATH_GOOGLE, {headers, body, method: "POST"})
            .then(res => {
                if (res.status < 500) {
                    return res.json().then(data => {
                        return {status: res.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw res;
                }
            })
            .then(res => {
                if (res.status === 200) {
                    dispatch({type: 'LOGIN_SUCCESSFUL', data: res.data});
                    return res.data;
                } else if (res.status === 403 || res.status === 401) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: res.data});
                    throw res.data;
                } else {
                    dispatch({type: "LOGIN_FAILED", data: res.data});
                    throw res.data;
                }
            })
    }
};

export const register = (email, password1, password2) => {
    return (dispatch, getState) => {
        let headers = {"Content-Type": "application/json"};
        let body = JSON.stringify({email, password1, password2});

        return fetch(PATH_REGISTER, {headers, body, method: "POST"})
            .then(res => {
                if (res.status < 500) {
                    return res.json().then(data => {
                        return {status: res.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw res;
                }
            })
            .then(res => {
                if (res.status === 200) {
                    dispatch({type: 'REGISTRATION_SUCCESSFUL', data: res.data});
                    return res.data;
                } else if (res.status === 403 || res.status === 401) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: res.data});
                    throw res.data;
                } else {
                    dispatch({type: "REGISTRATION_FAILED", data: res.data});
                    throw res.data;
                }
            })
    }
};

export const logout = () => {
    return (dispatch, getState) => {
        let headers = {"Content-Type": "application/json"};

        return fetch(PATH_LOGOUT, {headers, body: "", method: "POST"})
            .then(res => {
                if (res.status === 200) {
                    return {status: res.status, data: {}};
                } else if (res.status < 500) {
                    return res.json().then(data => {
                        return {status: res.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw res;
                }
            })
            .then(res => {
                if (res.status === 200) {
                    dispatch({type: 'LOGOUT_SUCCESSFUL'});
                    return res.data;
                } else if (res.status === 403 || res.status === 401) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: res.data});
                    throw res.data;
                }
            })
    }
};

export const verify_email = (key) => {
    return (dispatch, getState) => {
        let headers = {"Content-Type": "application/json"};
        let body = JSON.stringify({key});

        return fetch(PATH_VERIFY_EMAIL, {headers, body, method: "POST"})
            .then(res => {
                if (res.status < 500) {
                    return res.json().then(data => {
                        return {status: res.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw res;
                }
            })
            .then(res => {
                if (res.status === 200) {
                    dispatch({type: 'EMAIL_VERIFICATION_SUCCESSFUL', data: res.data});
                    return res.data;
                } else {
                    dispatch({type: "EMAIL_VERIFICATION_FAILED", data: res.data});
                    throw res.data;
                }
            })
    }
};
