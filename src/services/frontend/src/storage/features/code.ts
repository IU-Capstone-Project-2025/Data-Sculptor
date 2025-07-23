import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface CodeState {
  map: { [task_id: string]: string };
}

const initialState: CodeState = {
  map: {},
};

export const codeSlice = createSlice({
  name: "code",
  initialState,
  reducers: {
    setCode: (state, action: PayloadAction<[string, string]>) => {
      state.map[action.payload[0]] = action.payload[1];
    },
  },
});

export const { setCode } = codeSlice.actions;
export default codeSlice.reducer;
