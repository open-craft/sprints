import {PATH_DASHBOARD, USE_CACHE} from "../constants";
import {callApi} from "../middleware/api";

const prepareCellIds = (cells) => {
    const result = {};
    cells.forEach(cell => result[cell.board_id] = cell.name);

    return result;
};

export const loadCells = () => {
    return (dispatch) => {
        dispatch({type: "CELLS_LOADING"});

        return callApi(PATH_DASHBOARD)
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

export const loadBoard = (board_id, cache = false) => {
    let board_url = `${PATH_DASHBOARD}${board_id}/` + (cache ? `?${USE_CACHE}` : '');

    return (dispatch) => {
        dispatch({type: "BOARD_LOADING", board_id: board_id});

        return callApi(board_url)
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
    };
};
