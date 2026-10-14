package app.vladmir.storetest
import android.app.Activity
import android.os.Bundle
import android.widget.TextView
class MainActivity:Activity(){override fun onCreate(state:Bundle?){super.onCreate(state);setContentView(TextView(this).apply {text="Vladmir Store\nTeste de instalação\n"+packageManager.getPackageInfo(packageName,0).versionName;gravity=17;textSize=18f;setTextColor(0xffb7a2ff.toInt());setBackgroundColor(0xff101114.toInt())})}}
