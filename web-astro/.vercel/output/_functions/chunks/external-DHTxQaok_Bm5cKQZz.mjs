import { map, atom, computed, batched, onMount } from "nanostores";
import { deriveState } from "@clerk/shared/deriveState";
import { eventMethodCalled } from "@clerk/shared/telemetry";
const $csrState = map({
  isLoaded: false,
  client: void 0,
  user: void 0,
  session: void 0,
  organization: void 0
});
const $initialState = map();
const $clerk = atom(null);
computed([$csrState], (state) => state.isLoaded);
const $authStore = batched([$csrState, $initialState], (state, initialState) => {
  return deriveState(state.isLoaded, {
    session: state.session,
    user: state.user,
    organization: state.organization,
    client: state.client
  }, initialState);
});
computed([$authStore], (auth) => auth.user);
computed([$authStore], (auth) => auth.session);
const $organizationStore = computed([$authStore], (auth) => auth.organization);
const $clientStore = computed([$csrState], (csr) => csr.client);
const $clerkStore = computed([$clerk], (clerk) => clerk);
computed([$clientStore], (client) => client?.sessions);
const $signInStore = computed([$clientStore], (client) => client?.signIn);
const $signUpStore = computed([$clientStore], (client) => client?.signUp);
computed([$clerk], (clerk) => clerk?.billing);
const recordTelemetryEvent = (store, method) => {
  onMount(store, () => {
    $clerk.get()?.telemetry?.record(eventMethodCalled(method));
  });
};
recordTelemetryEvent($signInStore, "$signInStore");
recordTelemetryEvent($signUpStore, "$signUpStore");
recordTelemetryEvent($organizationStore, "$organizationStore");
export {
  $clerk as $,
  $csrState as a,
  $clerkStore as b,
  $initialState as c,
  $authStore as d
};
