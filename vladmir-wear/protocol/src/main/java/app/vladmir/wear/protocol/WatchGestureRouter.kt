package app.vladmir.wear.protocol
enum class WatchSwipe { VOICE, MENU }
/** Vertical gestures remain with Wear OS. */
class WatchGestureRouter(
    private val threshold:Float,
    private val edgeInsetFraction:Float=0.14f,
) {
 private var start:Pair<Float,Float>?=null
 private var safeWidth=0f
 private var startWasSafe=false
 fun down(x:Float,y:Float,width:Float){
  start=x to y
  safeWidth=width
  val inset=width*edgeInsetFraction
  startWasSafe=width>0f && x>=inset && x<=width-inset
 }
 fun cancel(){start=null}
 fun up(x:Float,y:Float,faceAuthorized:Boolean=false):WatchSwipe? {
  val point=start?:return null;start=null
  if(!faceAuthorized || !startWasSafe)return null
  val dx=x-point.first;val dy=y-point.second
  val inset=safeWidth*edgeInsetFraction
  if(x<inset || x>safeWidth-inset)return null
  if(kotlin.math.abs(dx)<threshold || kotlin.math.abs(dx)<kotlin.math.abs(dy)*1.5f)return null
  return if(dx>0)WatchSwipe.VOICE else WatchSwipe.MENU
 }
}
