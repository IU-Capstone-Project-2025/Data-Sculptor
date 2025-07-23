import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { Feedback } from "../../utils/api";

interface FeedbackState {
  map: { [task_id: string]: Feedback | undefined };
}

const initialState: FeedbackState = {
  map: {},
};

export const feedbackSlice = createSlice({
  name: "feedback",
  initialState,
  reducers: {
    setFeedback: (state, action: PayloadAction<[string, Feedback]>) => {
      state.map[action.payload[0]] = action.payload[1];
    },
  },
});

export const { setFeedback } = feedbackSlice.actions;
export default feedbackSlice.reducer;
