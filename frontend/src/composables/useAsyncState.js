import { reactive } from "vue";

function getDefaultErrorMessage(error) {
  return error?.response?.data?.message || error?.message || "请求失败";
}

export function useAsyncState(initialValue, options = {}) {
  const asyncState = reactive({
    state: "idle",
    data: initialValue,
    error: null,
    isIdle: true,
    isLoading: false,
    isSuccess: false,
    isEmpty: false,
    isError: false,
    reset,
    run,
    getErrorMessage: () => getDefaultErrorMessage(asyncState.error)
  });

  function setState(nextState) {
    asyncState.state = nextState;
    asyncState.isIdle = nextState === "idle";
    asyncState.isLoading = nextState === "loading";
    asyncState.isSuccess = nextState === "success";
    asyncState.isEmpty = nextState === "empty";
    asyncState.isError = nextState === "error";
  }

  function reset() {
    asyncState.data = initialValue;
    asyncState.error = null;
    setState("idle");
  }

  async function run(task, runOptions = {}) {
    const { preserveValue = false, emptyWhen = options.emptyWhen, onSuccess } = runOptions;

    setState("loading");
    asyncState.error = null;

    if (!preserveValue) {
      asyncState.data = initialValue;
    }

    try {
      const result = await task();
      asyncState.data = result;
      const shouldBeEmpty = typeof emptyWhen === "function" ? emptyWhen(result) : false;
      setState(shouldBeEmpty ? "empty" : "success");
      if (typeof onSuccess === "function") onSuccess(result);
      return result;
    } catch (err) {
      asyncState.error = err;
      setState("error");
      throw err;
    }
  }

  return asyncState;
}

export function getAsyncErrorMessage(error) {
  return getDefaultErrorMessage(error);
}