import {PATH_REFRESH_TOKEN} from "../constants";

const refreshToken = () => {
    const refresh = localStorage.getItem("refresh_token");
    const body = JSON.stringify({refresh: refresh});

    return callApi(PATH_REFRESH_TOKEN, body, "POST", true).then(res => {
        if (res.status === 200) {


        }
        return res;
    });
};

export const callApi = (endpoint, body = null, method = null, refresh_token = false) => {
    method = method ? method : body ? "POST" : "GET";
    let access_token = localStorage.getItem("access_token");

    let headers = {
        "Content-Type": "application/json",
    };

    if (access_token) {
        headers.Authorization = `Bearer ${access_token}`;
    }

    return fetch(endpoint, {headers, body, method: method}).then(res => {
        if (res.status === 401 && !refresh_token) {
            return refreshToken().then(ref => {
                if (ref.status === 200) {
                    return ref.json().then(json => {
                        headers.Authorization = `Bearer ${json.access}`;
                        localStorage.setItem("access_token", json.access);
                        localStorage.setItem("refresh_token", json.refresh);

                        return fetch(endpoint, {headers, body, method: method});
                    });
                }
                return res;
            });
        }
        return res;
    });
};
