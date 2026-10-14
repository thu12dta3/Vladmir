package app.vladmir.companion

import android.app.Notification
import android.app.NotificationManager
import android.content.*
import android.media.session.*
import android.os.SystemClock
import android.service.notification.*
import app.vladmir.wear.protocol.*
import org.json.*
import java.security.MessageDigest
import java.util.concurrent.*

object PhoneUtilities {
 fun access(c:Context)=c.getSystemService(NotificationManager::class.java).isNotificationListenerAccessGranted(ComponentName(c,MarkNotifications::class.java))
 fun media(c:Context,p:JSONObject):JSONObject {
  val prefs=c.getSharedPreferences("utilities",0);check(prefs.getBoolean("media",false) && access(c)){"MEDIA_PERMISSION_REQUIRED"}
  val sessions=c.getSystemService(MediaSessionManager::class.java).getActiveSessions(ComponentName(c,MarkNotifications::class.java))
  val current=sessions.firstOrNull {it.playbackState?.state==PlaybackState.STATE_PLAYING}?:sessions.firstOrNull()?:error("NO_ACTIVE_MEDIA")
  when(p.getString("action")) {
   "media_status"->require(p.length()==1)
   "media_control"->{require(p.length()==2);when(p.getString("command")){"play"->current.transportControls.play();"pause"->current.transportControls.pause();"next"->current.transportControls.skipToNext();"previous"->current.transportControls.skipToPrevious();else->error("UNSUPPORTED_MEDIA_CONTROL")}}
   else->error("UNSUPPORTED_ACTION")
  }
  val metadata=current.metadata
  return JSONObject().put("package",current.packageName).put("title",metadata?.getString(android.media.MediaMetadata.METADATA_KEY_TITLE)?.take(120)?:"Mídia ativa").put("playing",current.playbackState?.state==PlaybackState.STATE_PLAYING)
 }
}

/** Opt-in selected apps, title only, no disk queue or content logging. */
class MarkNotifications:NotificationListenerService(){
 private val work=ThreadPoolExecutor(1,1,0,TimeUnit.SECONDS,ArrayBlockingQueue<Runnable>(4))
 private val budget=NotificationBudget()
 private val dismissBudget=NotificationBudget()
 private fun selected(s:StatusBarNotification)=getSharedPreferences("utilities",0).getStringSet("notification_apps",emptySet()).orEmpty().contains(s.packageName)
 private fun notificationId(s:StatusBarNotification)=CompanionPolicy.hex(MessageDigest.getInstance("SHA-256").digest(s.key.toByteArray())).take(32)
 override fun onNotificationPosted(s:StatusBarNotification){
  if(!selected(s) || s.packageName==packageName || s.notification.visibility==Notification.VISIBILITY_SECRET || s.isOngoing || CompanionService.current?.connected!=true)return
  val title=s.notification.extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.take(120)?:return
  if(!budget.accept(SystemClock.elapsedRealtime()) || !WearProtocol.validText(title))return
  val id=notificationId(s)
  val appName=runCatching {packageManager.getApplicationLabel(packageManager.getApplicationInfo(s.packageName,0)).toString()}.getOrNull()?.take(80)?.takeIf {it.isNotBlank()}?:s.packageName.substringAfterLast('.')
  val category=s.notification.category?.takeIf {it in setOf(Notification.CATEGORY_MESSAGE,Notification.CATEGORY_EMAIL,Notification.CATEGORY_SOCIAL,Notification.CATEGORY_CALL,Notification.CATEGORY_EVENT,Notification.CATEGORY_REMINDER,Notification.CATEGORY_ALARM)}?:""
  val preview=if(s.packageName=="com.whatsapp") (s.notification.extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?:s.notification.extras.getCharSequence(Notification.EXTRA_TEXT))?.toString()?.trim()?.take(160).orEmpty() else ""
  val payload=JSONObject().put("action","notification").put("id",id).put("title",title).put("app",s.packageName).put("app_name",appName).put("category",category).put("preview",preview)
  try{work.execute {runCatching {CompanionService.current?.takeIf {it.connected}?.request(payload)}}}catch(_:RejectedExecutionException){}
 }
 override fun onNotificationRemoved(s:StatusBarNotification){
  if(!selected(s) || s.packageName==packageName || s.notification.visibility==Notification.VISIBILITY_SECRET || s.isOngoing || CompanionService.current?.connected!=true)return
  if(!dismissBudget.accept(SystemClock.elapsedRealtime()))return
  val payload=JSONObject().put("action","notification_cancel").put("id",notificationId(s)).put("app",s.packageName)
  try{work.execute {runCatching {CompanionService.current?.takeIf {it.connected}?.request(payload)}}}catch(_:RejectedExecutionException){}
 }
 override fun onDestroy(){work.shutdownNow();super.onDestroy()}
}
