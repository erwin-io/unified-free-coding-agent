import { Plugin } from "@opencode/plugin"

// Retry only transient free-capacity failures. OpenCode's built-in attempt
// ceiling still applies. The router chooses the available free provider again
// for every retry; this plugin never enables a paid model.
export default Plugin.define({
  id: "unified-free-capacity-retry",
  async setup(ctx) {
    await ctx.session.hook("retry", (event) => {
      const status = event.error.status
      if (status !== 429 && status !== 503 && status !== 502 && status !== 504) {
        return
      }
      if (event.attempt > 4) {
        event.decision = { retry: false }
        return
      }
      const delay = Math.min(60000, 10000 * (2 ** Math.max(0, event.attempt - 2)))
      event.decision = { retry: true, delay }
    })
  },
})
