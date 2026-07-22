async function createAsyncLocalStorage() {
  const { AsyncLocalStorage } = await import("node:async_hooks");
  return new AsyncLocalStorage();
}
const authAsyncStorage = await createAsyncLocalStorage();
export {
  authAsyncStorage as a
};
