const initialState = {
    cellsLoading: true,
    boardLoading: true,
    cells: JSON.parse(localStorage.getItem("cells")) || [],
    boards: JSON.parse(localStorage.getItem("boards")) || {},
};


export default function sprints(state=initialState, action) {
    let board;

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

            board = state.boards[action.board_id] || {};
            board.future_sprint = future_sprint;
            board.rows = rows;
            board.issues = issues;

            state.boards[action.board_id] = board;
            localStorage.setItem("boards", JSON.stringify(state.boards));
            return {...state, boardLoading: false};

        default:
            return state;
    }
}
