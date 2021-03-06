const initialState = {
    cellsLoading: true,
    boardLoading: true,
    cells: JSON.parse(localStorage.getItem("cells")) || [],
    boards: JSON.parse(localStorage.getItem("boards")) || {},
    buttons: {},
    button_messages: {}
};


export default function sprints(state=initialState, action) {

    switch (action.type) {

        case 'CELLS_LOADING':
            return {...state, cellsLoading: true};

        case 'BOARD_LOADING':
            return {...state, boardLoading: true};

        case 'CELLS_LOADED':
            localStorage.setItem("cells", JSON.stringify(action.cells));
            return {...state, cellsLoading: false, cells: action.cells};

        case 'BOARD_LOADED':
            const {future_sprint, rows, issues} = action.data;

            const board = state.boards[action.board_id] || {};
            board.future_sprint = future_sprint;
            board.rows = rows;
            board.issues = issues;

            state.boards[action.board_id] = board;
            localStorage.setItem("boards", JSON.stringify(state.boards));
            return {...state, boardLoading: false};

        case 'PERMISSION_GRANTED':
            state.buttons[action.action] = true;
            return {...state};

        case 'PERMISSION_DENIED':
            let data = action.data;
            if (data.detail) {
                data = data.detail;
            }
            state.button_messages[action.action] = data;
            return {...state};

        default:
            return state;
    }
}
