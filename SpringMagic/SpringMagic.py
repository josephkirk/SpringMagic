import maya.cmds as cmds
import pymel.core as pm
import pymel.core.datatypes as dt
import math
import maya.mel as mm
import copy
import os
import inspect

versionList=['v',0.1,2017,6,1]
version= ".".join([str(o) for o in versionList])
#################### Global Variable
sceneUnit= pm.currentUnit(l=True,q=True)
timeRange=1
pickMethod=1
startFrame = int(pm.playbackOptions(q=True,minTime=True))
endFrame = int(pm.playbackOptions(q=True,maxTime=True))
detailValue = 1
falloffValue = 1
dampValue=0.0
springValue=0.3
twistValue=0.3
loopValue=False
scriptName = inspect.getframeinfo(inspect.currentframe()).filename
scriptPath = os.path.dirname(os.path.abspath(scriptName))
scriptPath = "/".join(scriptPath.split('\\'))
mm.eval('source "%s/driveJointsWithHair.mel";' % scriptPath)
#################### UI Function Assign
#################### UI definition

#################### Function Definition
######## Misc Function
def getTimeRange(*arg):
    global startFrame
    global endFrame
    if timeRange:
        startFrame = int(pm.playbackOptions(q=True,minTime=True))
        endFrame = int(pm.playbackOptions(q=True,maxTime=True))
    else:
        startFrame=startFrame
        endFrame=endFrame
    sfef =(startFrame,endFrame)
    return sfef

def alignOb(alignOb,ob):
    alignObMatrix = pm.xform(alignOb,ws=True,q=True,m=True)
    pm.xform(ob,m=alignObMatrix)

def constraintOb(ob,tar):
    pm.pointConstraint(ob,tar)
    pm.orientConstraint(ob,tar)

def getTranslate(ob):
    tr = tuple(pm.xform(ob,ws=True,q=True,rp=True))
    return tr

def clearKeys(sfef):
    pm.cutKey(time=sfef)
######## Classic Spring Magic
def springPasteBonePose():
    print type(springUpAxis_comboBox.getSelect())

def springBindPose():
    pm.runtime.GoToBindPose()

def springStraightBonePose(bone):
    boneChain = getBoneChain(bone)
    if boneChain:
        for bone in boneChain[:-1]:
            bone.setRotation([0,0,0])
            bone.setAttr('rotateAxis', [0,0,0])
            bone.setAttr('jointOrient', [0,0,0])

def createEndJoint(bone):
    print bone
    if bone.getParent():
        jointRoot=bone.getParent()
        print jointRoot
        poList=[]
        for j in [bone,jointRoot]:
            print j
            poList.append(dt.Vector(pm.xform(j,q=True,ws=True,t=True)))
        endJointPos=(poList[0]-poList[1])*2+poList[0]
        print dt.length(poList[1]-poList[0])
        pm.select(bone,r=True)
        endJoint=pm.joint(p=endJointPos)
        pm.joint(bone,e=True,zso=True,oj='xyz')
        return endJoint

def createBoneFromSelection():
    bonObs =[]
    selection = pm.selected()
    if not selection:
        print "No Selection"
        return
    index = 0
    while index<len(selection):
        print index
        ob=selection[index]
        bonObs.append((cmds.joint(p=getTranslate(ob)),ob))
        #constraintOb(bonObs[index][0],bonObs[index][1])
        index+=1
    obRoot = pm.listRelatives(bonObs[0][1],p=True)
    endJoint=createEndJoint(bonObs[len(bonObs)-1][0])
    for obs in bonObs:
        pm.orientConstraint(obs[0],obs[1],mo=True)
    bonObs.append((endJoint,None))
    return bonObs

def createBone(Ob):
    pm.select(Ob,r=True)
    bonObs =[]
    obRoot = pm.listRelatives(Ob,p=True)
    obChain = getBoneChain(Ob)
    for s in obChain:
        index = obChain.index(s)
        bone =pm.joint(p=getTranslate(s))
        bonObs.append((pm.ls(bone)[0],s))
        if index==0:
            pm.parent(bone,obRoot)
        else:
            pm.joint(str(bonObs[index-1][0]),e=True,zso=True,oj='xyz')
        #pm.orientConstraint(bone,s,mo=True)
    endJoint=createEndJoint(bonObs[len(bonObs)-1][0])
    for obs in bonObs:
        pm.orientConstraint(obs[0],obs[1],mo=True)
    bonObs.append((endJoint,None))
    return bonObs

def getBoneChain(bone):
    # only apply on child bone, bacause need a parent bone move to cause the overlapping
    if not bone.getParent():
        return False
    
    # get bone chain, only get one stream, will not process branches
    boneChain = []
    boneChain.append( bone )
    childList = pm.listRelatives(bone,ad=1,typ='transform')
    childList.reverse()
    boneChain.extend(childList)
    return boneChain

def springApply(bone, pickedBones,springLoop=False,springRotateRate=0.3,springTwist=0.3):
    '''
    Get idea from max scripts 'SpringMagic' made by Sichuang Yuan, but make it more friendly with Maya
    '''

    # since maya 2016, there is a new animation evaluation mode called "Parallel" which supose to improve
    # the runtime performance of maya, but the new function seems cause some problem when calculate spring magic.
    # so I'll revert evaluation mode back to old way during calculation and set it back after

    # store evaluationManager mode for 2016 or newer
    if pm.versions.current() > 201600:
        currentMode = pm.evaluationManager( q=1, mode = 1 )[0]
        pm.evaluationManager( mode = 'off' )
    # Check Unit
    if sceneUnit!='cm':
        pm.currentUnit(l='cm')
    # get bone chain, only get one stream, will not process branches
    if pm.nodeType(bone)=='joint':
        boneChain = getBoneChain(bone)
    else:
        boneObs = createBone(bone)
        boneChain=[b[0] for b in boneObs]
    if not boneChain:
        return
    print boneChain
    boneRoot = boneChain[0].getParent()
    print boneRoot
    # get frame range
    pm.currentTime( startFrame, edit=True )

    # get bone chain start pose and key it
    boneStartRotation = {}
    # boneStartMatirx = {}
    for bone in boneChain:
        # reset bone rotate axis as 0
        bone.setRotation = bone.getAttr('rotateAxis')
        pm.xform(bone, ra = [0,0,0])
        # get bone start rotation pose
        boneStartRotation[bone] = bone.getRotation()
        # boneStartMatirx[bone] = bone.getAttr('matrix')

        if not springLoop:
            pm.setKeyframe(bone, attribute = 'rotate')
        # delete key not at start frame
        pm.cutKey( bone, time=(startFrame + 1,endFrame) )

    # get bone start world translation
    boneWorldTranlation = {}
    previousBoneWorldTranlation = {}
    previousBoneWorldRotation = {}
    previousBoneRotateAxis = None

    loopCount = float(springLoop)
    pickedBoneCount = float(len(pickedBones))
    boneChainCount = float(len(boneChain))
    frameCount = float(endFrame-startFrame)
    # caculate part
    for loop in range( int(loopCount+1) ):

        for frame in range( startFrame, endFrame+1 ):

            pm.currentTime( frame, edit=True )

            for bone in boneChain:

                # get bone world translation & matrix
                boneWorldTranlation[bone] = dt.Vector( pm.xform(bone, worldSpace = 1, translation = 1, query = 1) )
                # skip caculate at first frame
                if previousBoneWorldTranlation:
                    # skip end bone
                    if not bone == boneChain[-1]:
                        # get child bone name for caculate
                        childBone = boneChain[boneChain.index(bone) + 1]

                        # get the vector from current position to previous child position
                        boneAimVector = (boneWorldTranlation[bone] - previousBoneWorldTranlation[childBone]).normal()

                        # restore current bone rotation
                        boneCurrentRotation = bone.getRotation()

                        # reset bone to start pose
                        bone.setAttr('rotate', boneStartRotation[bone])

                        childBoneHight = pm.xform( childBone, worldSpace = 1, translation = 1, query = 1 )
                        
                        # get the vector of stance pose
                        stanceTranslation = ( childBone.getAttr('matrix') * childBone.getAttr('parentMatrix') ).translate
                        
                        boneStanceVetor = (boneWorldTranlation[bone] - stanceTranslation).normal()

                        # get rotation axis and degrees bewteen two vectors
                        boneRotateDegrees = math.degrees( boneStanceVetor.angle( boneAimVector ) )
                        boneRotateAxis = boneStanceVetor.axis( boneAimVector )

                        # if the rotate axis fliped
                        if previousBoneRotateAxis:
                            if abs(math.degrees( previousBoneRotateAxis.angle( boneRotateAxis ))) > 90: 
                                # then flip it back
                                boneRotateAxis = -boneRotateAxis
                                boneRotateDegrees = -boneRotateDegrees

                        previousBoneRotateAxis = boneRotateAxis

                        # set rotate rate
                        rotateRate = 1-float(springRotateRate)

                        upVector = dt.Vector(0,1,0)
                        rotateValue = upVector * (boneRotateDegrees*rotateRate)
                        # skip rotate bone if very close to start pose
                        if abs(boneRotateDegrees) > 0.001:

                            # match up bone and stance vector with aim constraint
                            lct = pm.spaceLocator()
                            lct.setTranslation( stanceTranslation )
                            cns = pm.aimConstraint( lct, bone, aimVector = [1,0,0], upVector = upVector, worldUpVector = boneRotateAxis )
                            # keep aim result before remove constraint
                            pm.setKeyframe(bone, attribute = 'rotate')
                            pm.delete( cns, lct )
                            # do rotate bone
                            pm.rotate(bone, rotateValue, objectSpace = 1, relative = 1)

                        else:
                            # use previous frame rotation
                            bone.setAttr('rotate', boneCurrentRotation)
                            pm.setKeyframe(bone, attribute = 'rotate')






                        # apply twist
                        twist = float(springTwist)
                        if 1 > twist:
                            # reset rotat x
                            bone.setAttr('rotateX', boneStartRotation[bone][0] )
                            # creat locator with stance rotation, slow step setMatrix, need optmaize
                            lct = pm.spaceLocator()
                            lct.setRotation(pm.xform(bone,q=1,worldSpace=1,rotation=1))
                            lct_p = pm.spaceLocator()
                            lct_p.setRotation(previousBoneWorldRotation[bone])
                            # get twist delay value
                            # creat orient constraint
                            cns_X = pm.orientConstraint( lct, lct_p, bone, skip = ['y','z'] )

                            # apply twist value to constraint
                            cns_X.setAttr(lct+'W0', twist)
                            cns_X.setAttr(lct_p+'W1', 1-twist)
                            # set rotate interp as shortest
                            cns_X.setAttr('interpType', 2)

                            # get caculated x
                            boneRotateX = bone.getAttr('rotateX')
                            # apply new rotate x
                            bone.setAttr('rotateX', boneRotateX)
                            pm.setKeyframe(bone, attribute = 'rotate')

                            pm.delete( cns_X, lct, lct_p )

                # save for next frame use
                previousBoneWorldRotation[bone] = pm.xform(bone,q=1,worldSpace=1,rotation=1)
                # print previousBoneWorldRotation[bone]
                #runProgressBar( main_progressBar, 1/(loopCount+1)*(1/pickedBoneCount)*(1/boneChainCount)*(1/(frameCount+1))*100 )
            # save for next frame use
            previousBoneWorldTranlation = copy.copy(boneWorldTranlation)

    if pm.nodeType(bone)!='joint':
        for o in boneObs:
            if o[1]:
                pm.bakeResults(o[1],at=['rotate'], t=(startFrame,endFrame))
        pm.delete(boneChain)
    #return Unit
    pm.currentUnit(l=sceneUnit)
    # revert evaluationManager mode for 2016 or newer
    if pm.versions.current() > 201600:
        pm.evaluationManager( mode = currentMode )

####### Hair Base Spring 

def bakeAnimFromOb(targetOb,bakeOb,startFrame,endFrame):
    f=startFrame
    while f<=endFrame:
        pm.setCurrentTime(f)
        alignOb(targetOb,bakeOb)
        pm.setKeyframe(bakeOb,at='translate')
        pm.setKeyframe(bakeOb,at='rotate')
        f+=1

def bakeAnimTuple(tupleOb,startFrame,endFrame):
    f=startFrame
    while f<=endFrame:
        pm.setCurrentTime(f)
        for o in tupleOb:
            alignOb(o[0],o[1])
            pm.setKeyframe(o[1],at='translate')
            pm.setKeyframe(o[1],at='rotate')
        f+=1

def makeDynamic(bone):
    if sceneUnit!='cm':
        pm.currentUnit(l='cm')
    if pm.nodeType(bone)=='joint':
        boneChain = getBoneChain(bone)
    else:
        boneObs = createBone(bone)
        boneChain=getBoneChain(boneObs[0][0])
        print bone,boneObs,boneChain
    if not boneChain:
        return
    pm.select([boneChain[0],boneChain[len(boneChain)-1]],r=True)
    driveJointsWithHair(detailValue,falloffValue)
    hairHandle=pm.ls('hairHandle1')[0]
    hairHandle.setAttr("hairDamping",dampValue)
    if pm.nodeType(bone)=='joint':
        pm.bakeResults(bone,at=['rotate'],hi='below',sm=True,t=getTimeRange())
        pm.delete('dynJoint*','nucleus*','follicle*')
    else:
        for o in boneObs:
            if o[1]:
                pm.bakeResults(o[1],at=['rotate'],t=getTimeRange(),sm=True)
        pm.delete(boneObs[0][0],'dynJoint*','nucleus*','follicle*',hi='below')
    pm.currentUnit(l=sceneUnit)
    #bakeIt(boneObs)
def checkPlaySpeed():
    playSpeed = pm.playbackOptions(q=True,ps=True)
    if playSpeed:
        cD=pm.confirmDialog(title="PlaySpeedCheck",message="For best results please set playback speed to: play every frame\n\n",messageAlign='Center',button=["Yes","No"],defaultButton="Yes",cancelButton="No",dismissString="No")
        if cD == "Yes":
            pm.playbackOptions(ps=0)

def driveJointsWithHair(detail,falloff):
    mm.eval('driveJointsWithHair %s %s;' % (detail,falloff))
    pm.hide('hairHandle*','hairSystem*')

############ Main Function
def springIt(method):
    if pm.ls(sl=1, type='joint'):
        pickedBones = pm.ls(sl=1, type='joint')
    elif pm.ls(sl=1):
        pickedBones = pm.ls(sl=1)
    else:
        return False
    for bone in pickedBones:
        if method:
            makeDynamic(bone)
        else:
            springApply(bone,pickedBones,springLoop=loopValue,springRotateRate=springValue,springTwist=twistValue)

############ UI Function
def nulldef():
    print(tempJoints)
def removeUI():
    pm.deleteUI('makeSpringWin')
def changeDVal(val):
    global detailValue
    detailValue=val
def changeFVal(val):
    global falloffValue
    falloffValue=val
def changeDaVal(val):
    global dampValue
    dampValue=val
def changeSprVal(val):
    global springValue
    springValue=val
def changeTwsVal(val):
    global twistValueValue
    twistValue=val
    print twistValue
def changeLoopVal(val):
    global loopValue
    loopValue=val
    print loopValue
def changeTRangeVal(val):
    global timeRange
    timeRange=val
    print timeRange
def changeSFVal(val):
    global startFrame
    startFrame=val
    print startFrame
def changeEFVal(val):
    global endFrame
    endFrame=val
    print endFrame
def InteractivePlayback():
    pm.setCurrentTime(pm.playbackOptions(q=True,minTime=True))
    mm.eval('InteractivePlayback;')
    pm.setCurrentTime(pm.playbackOptions(q=True,minTime=True))
def clearAnim():
    clearKeys((startFrame,endFrame))
    pm.currentTime(startFrame,edit=True)
def makeSpringUI():
    if pm.window('makeSpringWin',ex=True):
        pm.deleteUI('makeSpringWin',window=True)
        pm.windowPref('makeSpringWin',remove=True)
    pm.window('makeSpringWin',t="Spring Magic Maya %s" % version)
    pm.scrollLayout('scrollLayout')
    pm.frameLayout(label="")
    pm.columnLayout(adjustableColumn=1)
    pm.rowColumnLayout(numberOfColumns=3,columnWidth=[(1,90),(2,60),(3,90)])
    pm.text(label="Method: ")
    dynMethodID = pm.radioCollection()
    pm.radioButton(label="Chain",select=True)
    pm.radioButton(label="Selection")
    pm.setParent('..')
    pm.rowColumnLayout(numberOfColumns=6,columnWidth=[(1,90),(2,60),(3,55),(4,45),(5,30),(6,45)])
    pm.text(label="Key Range: ")
    dynkeyRange = pm.radioCollection()
    pm.radioButton(label="Active",select=True,onc=lambda *arg:changeTRangeVal(1))
    pm.radioButton(label="From: ",onc=lambda *arg:changeTRangeVal(0))
    pm.intField(value=startFrame,cc=changeSFVal)
    pm.text(label="To: ")
    pm.intField(value=endFrame,cc=changeEFVal)
    pm.setParent('..')
    pm.setParent('..')
    pm.frameLayout(label='Hair Magic',borderStyle='in')
    pm.rowColumnLayout(numberOfColumns=2,columnWidth=[(1,90),(2,180)])
    pm.text(label="Hair Damping: ",align='right')
    pm.floatField(min=0.0, max=1, value=0, step=0.1, cc=changeDaVal)
    pm.setParent('..')
    pm.rowColumnLayout(numberOfColumns=4,columnWidth=[(1,90),(2,60),(3,60),(4,85)])
    pm.text(label="Hair Stiffness : ",align='right')
    dynJointFalloffID = pm.radioCollection()
    pm.radioButton(label="Normal",onc=lambda *arg:changeFVal(0))
    pm.radioButton(label="Quick",select=True,onc=lambda *arg:changeFVal(1))
    pm.radioButton(label="Slow",onc=lambda *arg:changeFVal(2))
    pm.text(label="Hair Detail : ",align='right')
    dynJointDetailID = pm.radioCollection()
    pm.radioButton(label="Low",onc=lambda *arg:changeDVal(0))
    pm.radioButton(label="Medium",select=True,onc=lambda *arg:changeDVal(1))
    pm.radioButton(label="High",onc=lambda *arg:changeDVal(2))
    pm.setParent('..')
    pm.setParent('..')
    pm.frameLayout(label='Spring Magic',borderStyle='in')
    pm.rowColumnLayout(numberOfColumns=3,columnWidth=[(1,120),(2,140),(3,60)])
    pm.rowColumnLayout(numberOfColumns=2,columnWidth=[(1,60),(2,60)])
    pm.text(label="Spring : ",align='right')
    pm.floatField(minValue=0, maxValue=1, value=0.3,editable=True,cc=changeSprVal)
    pm.setParent('..')
    pm.rowColumnLayout(numberOfColumns=2,columnWidth=[(1,60),(2,60)])
    pm.text(label="Twist : ",align='right')
    pm.floatField(minValue=0, maxValue=1, value=0.3,editable=True,cc=changeTwsVal)
    pm.setParent('..')
    pm.checkBox(label="Loop",cc=changeLoopVal)
    pm.setParent('..')
    pm.setParent('..')
    pm.rowColumnLayout(numberOfColumns=3,columnWidth=[(1,112),(2,112),(3,112)])
    pm.button(label="Spring Magic",c=lambda *arg:springIt(0))
    pm.button(label="Hair Magic",c=lambda *arg:springIt(1))
    pm.button(label="Clear",c=lambda *arg:clearAnim())
    pm.showWindow()
