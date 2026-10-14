package app.vladmir.wear.protocol
import org.junit.Test
import org.junit.Assert.*
class WatchGestureRouterTest {
 @Test fun horizontal(){val g=WatchGestureRouter(80f);g.down(100f,200f,400f);assertEquals(WatchSwipe.VOICE,g.up(300f,205f,true));g.down(300f,200f,400f);assertEquals(WatchSwipe.MENU,g.up(100f,205f,true))}
 @Test fun vertical(){val g=WatchGestureRouter(80f);g.down(200f,50f,400f);assertNull(g.up(202f,350f,true));g.down(200f,350f,400f);assertNull(g.up(200f,50f,true))}
 @Test fun tapAndCancel(){val g=WatchGestureRouter(80f);g.down(100f,100f,400f);assertNull(g.up(110f,100f,true));g.down(20f,100f,400f);g.cancel();assertNull(g.up(350f,100f,true));assertNull(g.up(350f,100f,true))}
 @Test fun diagonal(){val g=WatchGestureRouter(80f);g.down(100f,100f,400f);assertNull(g.up(220f,200f,true))}
 @Test fun faceMustAuthorizeTouch(){val g=WatchGestureRouter(80f);g.down(100f,100f,400f);assertNull(g.up(300f,105f));g.down(100f,100f,400f);assertEquals(WatchSwipe.VOICE,g.up(300f,105f,true))}
 @Test fun systemEdgeGesturesAreNotRouted(){val g=WatchGestureRouter(80f);g.down(2f,200f,400f);assertNull(g.up(240f,205f,true));g.down(398f,200f,400f);assertNull(g.up(160f,205f,true));g.down(100f,200f,400f);assertNull(g.up(398f,205f,true))}
}
