import { configureStore } from "@reduxjs/toolkit";
import codeReducer from "./features/code";
import feedbackReducer from "./features/feedback";

export const store = configureStore({
  reducer: {
    code: codeReducer,
    feedback: feedbackReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export default store;
