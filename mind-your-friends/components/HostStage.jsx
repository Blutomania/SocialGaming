'use client';

// Reserved space for the AI host's avatar (playtest note 6). Empty on
// purpose — there is no avatar yet, and the point of building the slot now is
// that every screen gets laid out around a host that exists, instead of being
// laid out without one and rearranged later.
//
// 9:16, matching modern vertical video (TikTok's 1080x1920). That's the shape
// a generated talking-head clip will arrive in, so the layout should be
// holding exactly that hole rather than something the video has to be
// letterboxed into.
//
// Desktop only. On a phone the screen IS the vertical video shape — giving
// the host a 9:16 slot there would leave no room for the game, so the host
// waits until there's width to spare.
export default function HostStage() {
  return (
    <aside className="hidden lg:block">
      <div className="sticky top-8">
        <div
          className="flex w-full items-center justify-center rounded-lg border border-dashed border-gray-700 bg-black/30"
          style={{ aspectRatio: '9 / 16' }}
        >
          <div className="px-4 text-center">
            <p className="text-4xl">🎙️</p>
            <p className="mt-2 text-sm font-semibold text-gray-500">Your host</p>
            <p className="mt-1 text-xs text-gray-600">Coming soon</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
