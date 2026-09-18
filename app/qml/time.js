.pragma library

function format(seconds) {
    const t = Math.max(0, seconds)
    const m = Math.floor(t / 60)
    const s = (t - m * 60).toFixed(2).padStart(5, "0")
    return m + ":" + s
}
