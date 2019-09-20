import {PARAM_BOARD_ID, PATH_CELLS, PATH_DASHBOARD} from "../constants";

const prepareCellIds = (cells) => {
    const result = {};
    for (const cell of cells) {
        result[cell.board_id] = cell.name;
    }

    return result;
};

export const loadCells = () => {
    return (dispatch, getState) => {
        dispatch({type: "CELLS_LOADING"});

        let token = getState().auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        return fetch(PATH_CELLS, {headers,})
            .then(response => {
                if (response.status < 500) {
                    return response.json().then(data => {
                        return {status: response.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw response;
                }
            })
            .then(result => {
                if (result.status === 200) {
                    const cells = prepareCellIds(result.data);
                    dispatch({type: 'CELLS_LOADED', cells: cells});
                    return cells;
                } else if (result.status >= 400 && result.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: result.data});
                    throw result.data;
                }
            });
    }
};

export const loadBoard = (board_id) => {
    let board_url = `${PATH_DASHBOARD}?${PARAM_BOARD_ID}${board_id}`;

    return (dispatch, getState) => {
        dispatch({type: "BOARD_LOADING", board_id: board_id});

        let token = getState().auth.token;
        let headers = {
            "Content-Type": "application/json",
        };
        if (token) {
            headers["Authorization"] = `JWT ${token}`;
        }

        return fetch(board_url, {headers,})
            .then(response => {
                if (response.status < 500) {
                    return response.json().then(data => {
                        return {status: response.status, data};
                    })
                } else {
                    console.log("Server Error!");
                    throw response;
                }
            })
            .then(result => {
                if (result.status === 200) {
                    result.data.rows.sort((x, y) => (x.name > y.name) ? 1 : -1);
                    result.data.issues.sort((x, y) => {
                        if (x.current_sprint !== y.current_sprint) {
                            return (x.current_sprint > y.current_sprint) ? -1 : 1
                        }
                        return (x.key > y.key) ? 1 : -1
                    });

                    dispatch({type: 'BOARD_LOADED', board_id: board_id, data: result.data});
                    return result.data;
                } else if (result.status >= 400 && result.status < 500) {
                    dispatch({type: "AUTHENTICATION_ERROR", data: result.data});
                    throw result.data;
                }
            });
    }
};
