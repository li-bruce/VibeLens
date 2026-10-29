/** Resolve an actual application screenshot at the selected recording position. */
export function applicationAt(artifact, eventId, language = "en") {
  const events = artifact.recording.events;
  const index = events.findIndex((event) => event.id === eventId);
  if (index < 0) return null;
  const eligible = new Set(events.slice(0, index + 1).map((event) => event.id));
  const frames = artifact.application_frames.filter((frame) => eligible.has(frame.event_id));
  const frame = frames.at(-1);
  if (!frame) return null;
  return {
    ...frame,
    image: frame.images[language] || frame.images.en,
    eventId,
  };
}
